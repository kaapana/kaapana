import glob
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
import zipfile
from collections import Counter
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse

import requests
from integration_tests.utils.KaapanaAuth import KaapanaAuth
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__, logging.INFO)

TCIA_GETIMAGE_URL = os.getenv(
    "TCIA_GETIMAGE_URL",
    "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage",
)
# (connect, next chunk) in seconds. Neither bounds the whole transfer.
HTTP_TIMEOUT = (10, 60)
TCIA_TIMEOUT = (10, int(os.getenv("TCIA_TIMEOUT", "60")))
TCIA_ATTEMPTS = int(os.getenv("TCIA_ATTEMPTS", "3"))


class SeriesUnavailable(Exception):
    """A source could not deliver a series."""


class DataEndpoints(KaapanaAuth):
    def __init__(self, host, client_secret):
        super().__init__(host, client_secret)

    def get_dataset_from_backend(self, dataset):
        r = self.request(
            "kaapana-backend/client/dataset",
            request_type=requests.get,
            params={"name": dataset},
            raise_for_status=False,
        )
        return r.json()

    def check_if_dataset_complete(self, kaapana_dataset: str, series_uids: list):
        """
        Request the dataset from the kaapana-backend and check if it consists of the the same identifiers as the ids in series_uids.
        Return true if all series are found else false.
        """
        logger.info(f"Check if dataset {kaapana_dataset} is complete.")
        try:
            backend_dataset = self.get_dataset_from_backend(kaapana_dataset)
        except:
            logger.warning(
                f"Request to backend failed! Suppose not all series found for dataset {kaapana_dataset=}."
            )
            return False

        if backend_dataset.get("detail", None) == "Dataset not found":
            return False

        identifiers = backend_dataset.get("identifiers") or []
        missing = set(series_uids) - set(identifiers)
        if not missing:
            return True
        logger.warning("Dataset missing identifiers: %s", sorted(missing))
        return False

    def wait_for_dataset(self, source_file: Path, kaapana_dataset: str, max_time=2400):
        """
        Wait until the dataset is completly available in the kaapana-backend.
        """
        series_uids = get_series_to_download_from_manifest(source_file)
        start_time = time.time()
        while abs(start_time - time.time()) < max_time:
            time.sleep(15)
            if self.check_if_dataset_complete(
                kaapana_dataset=kaapana_dataset, series_uids=series_uids
            ):
                logger.info(
                    f"All series uids found as identifiers in dataset {kaapana_dataset=}. Dataset is complete. Stop waiting."
                )
                return

        logger.error(f"Waiting for {kaapana_dataset} exceeds {max_time=}")
        raise TimeoutError(f"Waiting for {kaapana_dataset} exceeds {max_time=}")

    def check_running_dags(self, dag_id):
        r = self.request("kaapana-backend/workflows/running", request_type=requests.get)
        list_of_dags = r.json()
        if dag_id in list_of_dags:
            return True
        return False

    def check_if_service_dags_finished(self, max_time=300):
        start = time.time()
        while self.check_running_dags(
            "service-extract-metadata"
        ) or self.check_running_dags("service-process-incoming-dcm"):
            if abs(time.time() - start) > max_time:
                return False
        return True


def send_data(source_directory: Path, host: str, kaapana_dataset: str):
    """
    Send dicom files from directory dir to the host PACS on port 11112 with aetitle aetitle.
    Return a list of send dicoms
    """
    project = "admin"
    report = os.path.join(source_directory, "report.txt")
    command = f"dcmsend {host} 11112 --scan-directories --call kp-{project} --aetitle kp-{kaapana_dataset} --create-report-file {report} --scan-pattern *.dcm --recurse {source_directory}".split()
    logger.info(f"Start sending data to {project=} and dataset {kaapana_dataset=}")
    run = subprocess.run(command)
    try:
        run.check_returncode()
        logger.info(f"Successfully send data with {kaapana_dataset=}")
    except subprocess.CalledProcessError as e:
        logger.warning(str(e))


def get_series_to_download_from_manifest(file_path: Path):
    regex = re.compile(r"[0-9\.]*")
    series_uids = []
    with open(file_path, "r") as f:
        for line in f:
            if (uid := regex.match(line)) and (uid.group() != ""):
                series_uids.append(uid.group())
    return series_uids


def fetch_archive(source_dir, dataset: str, name: str) -> bytes:
    archive = Path(source_dir) / dataset / name
    if not archive.is_file():
        raise SeriesUnavailable(f"{archive} does not exist")
    try:
        payload = archive.read_bytes()
    except OSError as error:
        raise SeriesUnavailable(f"reading {archive} failed: {error}") from error
    if not payload:
        raise SeriesUnavailable(f"{archive} is empty")
    return payload


def fetch_from_tcia(series_uid: str) -> bytes:
    last_error = None
    for attempt in range(1, TCIA_ATTEMPTS + 1):
        try:
            response = requests.get(
                TCIA_GETIMAGE_URL,
                params={"SeriesInstanceUID": series_uid},
                timeout=TCIA_TIMEOUT,
            )
            response.raise_for_status()
            return response.content
        except requests.RequestException as error:
            last_error = error
            logger.debug(f"TCIA attempt {attempt}/{TCIA_ATTEMPTS} failed: {error}")
    raise SeriesUnavailable(f"TCIA did not deliver {series_uid}: {last_error}")


def fetch_from_url(url: str) -> bytes:
    try:
        response = requests.get(url, timeout=HTTP_TIMEOUT)
        response.raise_for_status()
        return response.content
    except requests.RequestException as error:
        raise SeriesUnavailable(f"{url} did not deliver: {error}") from error


def extract_archive(payload: bytes, outdir: str):
    """Unpacking is what validates a payload, so a bad one falls through."""
    try:
        with zipfile.ZipFile(BytesIO(payload)) as content:
            content.extractall(outdir)
    except (zipfile.BadZipFile, OSError) as error:
        raise SeriesUnavailable(f"unpacking into {outdir} failed: {error}") from error


def cache_archive(cache_dir, dataset: str, name: str, payload: bytes):
    archive = Path(cache_dir) / dataset / name
    if archive.is_file():
        return
    half_written = archive.with_name(f"{name}.{uuid.uuid4().hex[:8]}")
    try:
        archive.parent.mkdir(parents=True, exist_ok=True)
        half_written.write_bytes(payload)
        os.replace(half_written, archive)
    except OSError as error:
        logger.warning(f"could not cache {archive}: {error}")
        half_written.unlink(missing_ok=True)


def list_of_series_in_dir(dir):
    list_of_series = []
    dicom_files = glob.glob(os.path.join(dir, "**/*.dcm"), recursive=True)
    for file in dicom_files:
        if (
            series_uid := os.path.dirname(file).split("/")[-1]
        ) and series_uid not in list_of_series:
            list_of_series.append(series_uid)
    return list_of_series


def clone_test_data_repo(entry: dict, dest: Path) -> Path:
    url, token = entry["url"], entry.get("token", "")
    path = entry.get("path", "ci_integration_tests")
    authed_url = (
        url.replace("https://", f"https://oauth2:{token}@", 1) if token else url
    )
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
    shutil.rmtree(dest, ignore_errors=True)
    for cmd in (
        [
            "git",
            "clone",
            "--quiet",
            "--depth",
            "1",
            "--sparse",
            "--filter=blob:none",
            "--branch",
            entry.get("ref", "main"),
            authed_url,
            str(dest),
        ],
        ["git", "-C", str(dest), "sparse-checkout", "set", path],
    ):
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            shutil.rmtree(dest, ignore_errors=True)
            without_token = result.stderr.strip().replace(authed_url, url)
            raise SeriesUnavailable(
                without_token.replace(token, "***") if token else without_token
            )
    return dest / path


def clone_test_data_repos(spec: str, dest_root: Path) -> list:
    if os.path.isfile(spec):
        spec = Path(spec).read_text()
    try:
        entries = json.loads(spec)
    except json.JSONDecodeError as error:
        logger.warning(f"test-data repositories are not valid JSON, ignoring: {error}")
        return []

    dirs = []
    for n, entry in enumerate(entries, start=1):
        unshared_dest = Path(dest_root) / f"test_data_repo_{n}.{os.getpid()}"
        try:
            repo_dir = clone_test_data_repo(entry, unshared_dest)
        except (SeriesUnavailable, KeyError, OSError) as error:
            logger.warning(f"repository {n} ({entry.get('url')}) not cloned: {error}")
            continue
        logger.info(f"cloned {entry.get('url')} to {repo_dir}")
        dirs.append(str(repo_dir))
    return dirs


@lru_cache(maxsize=None)
def cloned_repo_dirs(spec: str, dest_root: str) -> tuple:
    return tuple(clone_test_data_repos(spec, Path(dest_root))) if spec else ()


def dataset_archives(source_file: Path, target_dir: Path):
    """
    Every archive a dataset is made of, as (cache name, unpack dir, fetch).

    A .tcia manifest lists one archive per series; anything else is a list of
    urls, one archive each. Both end up cached as <dataset>/<name>.
    """
    if str(source_file).endswith(".tcia"):
        for series_uid in get_series_to_download_from_manifest(source_file):
            yield (
                f"{series_uid}.zip",
                os.path.join(target_dir, series_uid, series_uid),
                "TCIA",
                lambda uid=series_uid: fetch_from_tcia(uid),
            )
        return

    for line in Path(source_file).read_text().splitlines():
        if not (url := line.strip()):
            continue
        name = os.path.basename(urlparse(url).path) or "download.zip"
        yield (
            name,
            os.path.join(target_dir, Path(name).stem),
            urlparse(url).netloc or "origin",
            lambda u=url: fetch_from_url(u),
        )


def archive_sources(name, dataset, cache_dir, repo_dirs, remote_label, remote):
    """A generator so repo_dirs() only clones once the cache has missed."""
    if cache_dir:
        yield "cache", lambda: fetch_archive(cache_dir, dataset, name), False
    for repo_dir in repo_dirs() if callable(repo_dirs) else repo_dirs or []:
        yield "data repo", lambda d=repo_dir: fetch_archive(d, dataset, name), True
    yield remote_label, remote, True


def download_archive(
    name, outdir, remote_label, remote, dataset, cache_dir=None, repo_dirs=None
):
    failures = []
    for label, fetch, worth_caching in archive_sources(
        name, dataset, cache_dir, repo_dirs, remote_label, remote
    ):
        try:
            payload = fetch()
            extract_archive(payload, outdir)
        except SeriesUnavailable as error:
            failures.append(f"{label}: {error}")
            logger.debug(f"{name}: {label} did not deliver it, {error}")
            continue
        if worth_caching and cache_dir:
            cache_archive(cache_dir, dataset, name, payload)
        return label

    raise SeriesUnavailable(f"{name} unavailable -> " + " | ".join(failures))


@lru_cache(maxsize=None)
def warn_cache_dir_missing(cache_dir: str):
    logger.warning(
        f"cache directory {cache_dir} does not exist — on a runner this usually "
        "means the volume is not mounted into the job"
    )


def already_unpacked(outdir) -> bool:
    path = Path(outdir)
    return path.is_dir() and any(path.iterdir())


def download_data(
    source_file: Path, target_dir: Path, force=False, cache_dir=None, repo_dirs=None
):
    """Collect every archive of one dataset, cache first and origin last."""
    dataset = Path(target_dir).name
    archives = list(dataset_archives(source_file, target_dir))
    order = (
        (["cache"] if cache_dir else [])
        + (["data repo"] if repo_dirs else [])
        + sorted({label for _, _, label, _ in archives})
    )
    logger.info(f"{dataset}: {len(archives)} archives, sources: {' -> '.join(order)}")
    if cache_dir and not Path(cache_dir).is_dir():
        warn_cache_dir_missing(str(cache_dir))

    served = Counter()
    unavailable = []
    for name, outdir, remote_label, remote in archives:
        if already_unpacked(outdir) and not force:
            served["already on disk"] += 1
            continue
        try:
            served[
                download_archive(
                    name, outdir, remote_label, remote, dataset, cache_dir, repo_dirs
                )
            ] += 1
        except SeriesUnavailable as error:
            unavailable.append(str(error))

    summary = ", ".join(f"{count} from {label}" for label, count in served.items())
    logger.info(f"{dataset}: {summary or 'nothing collected'}")
    if unavailable:
        for failure in unavailable:
            logger.error(f"{dataset}: {failure}")
        raise SeriesUnavailable(
            f"{dataset}: {len(unavailable)} of {len(archives)} archives unavailable"
        )
