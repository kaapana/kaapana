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

import requests
from integration_tests.utils.KaapanaAuth import KaapanaAuth
from integration_tests.utils.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)

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


def download_from_url(output_dir, input_file="download-urls.txt"):
    """
    Download files from urls specified in `dir/download-urls.txt`, save into `output` and unzip `output`.
    """
    with open(input_file, "r") as f:
        for url in f:
            r = requests.get(url, timeout=HTTP_TIMEOUT)
            content = zipfile.ZipFile(BytesIO(r.content))
            content.extractall(output_dir)


def fetch_archive(source_dir, dataset: str, series_uid: str) -> bytes:
    archive = Path(source_dir) / dataset / f"{series_uid}.zip"
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
            logger.warning(
                f"TCIA attempt {attempt}/{TCIA_ATTEMPTS} for {series_uid} failed: {error}"
            )
    raise SeriesUnavailable(f"TCIA did not deliver {series_uid}: {last_error}")


def extract_archive(payload: bytes, outdir: str):
    """Unpacking is what validates a payload, so a bad one falls through."""
    try:
        with zipfile.ZipFile(BytesIO(payload)) as content:
            content.extractall(outdir)
    except (zipfile.BadZipFile, OSError) as error:
        raise SeriesUnavailable(f"unpacking into {outdir} failed: {error}") from error


def cache_archive(cache_dir, dataset: str, series_uid: str, payload: bytes):
    archive = Path(cache_dir) / dataset / f"{series_uid}.zip"
    if archive.is_file():
        return
    half_written = archive.with_name(f"{archive.name}.{uuid.uuid4().hex[:8]}")
    try:
        archive.parent.mkdir(parents=True, exist_ok=True)
        half_written.write_bytes(payload)
        os.replace(half_written, archive)
    except OSError as error:
        logger.warning(f"could not cache {series_uid} at {archive}: {error}")
        half_written.unlink(missing_ok=True)
    else:
        logger.info(f"cached {series_uid} at {archive}")


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
        logger.info(
            f"cloned repository {n} ({entry.get('url')}) to {repo_dir}, "
            f"{len(list(repo_dir.glob('**/*.zip')))} series archives"
        )
        dirs.append(str(repo_dir))
    return dirs


@lru_cache(maxsize=None)
def cloned_repo_dirs(spec: str, dest_root: str) -> tuple:
    return tuple(clone_test_data_repos(spec, Path(dest_root))) if spec else ()


def series_sources(series_uid: str, dataset: str, cache_dir, repo_dirs):
    """A generator so repo_dirs() only clones once the cache has missed."""
    if cache_dir:
        yield (
            f"cache {cache_dir}",
            lambda: fetch_archive(cache_dir, dataset, series_uid),
            False,
        )
    for repo_dir in repo_dirs() if callable(repo_dirs) else repo_dirs or []:
        yield (
            f"repository {repo_dir}",
            lambda d=repo_dir: fetch_archive(d, dataset, series_uid),
            True,
        )
    yield "TCIA", lambda: fetch_from_tcia(series_uid), True


def download_series(
    series_uid: str, dataset: str, series_outdir: str, cache_dir=None, repo_dirs=None
):
    failures = []
    for label, fetch, worth_caching in series_sources(
        series_uid, dataset, cache_dir, repo_dirs
    ):
        logger.info(f"{series_uid}: getting it from {label}")
        try:
            payload = fetch()
            extract_archive(payload, os.path.join(series_outdir, series_uid))
        except SeriesUnavailable as error:
            failures.append(f"{label}: {error}")
            logger.warning(f"{series_uid}: {label} did not deliver it, {error}")
            continue
        logger.info(f"{series_uid}: got it from {label}")
        if worth_caching and cache_dir:
            cache_archive(cache_dir, dataset, series_uid, payload)
        return label

    raise SeriesUnavailable(
        f"{series_uid} unavailable from all source(s) -> " + " | ".join(failures)
    )


def download_data(
    source_file: Path, target_dir: Path, force=False, cache_dir=None, repo_dirs=None
):
    """Collect a .tcia manifest via download_series(), or a url list directly."""
    if str(source_file).endswith(".tcia"):
        series_uids = get_series_to_download_from_manifest(source_file)
        dataset = Path(target_dir).name
        order = (
            ([f"cache {cache_dir}"] if cache_dir else [])
            + (["test-data repositories"] if repo_dirs else [])
            + ["TCIA"]
        )
        logger.info(
            f"collecting {dataset}: {len(series_uids)} series, "
            f"sources tried in this order: {' then '.join(order)}"
        )
        if cache_dir and not Path(cache_dir).is_dir():
            logger.warning(
                f"cache directory {cache_dir} does not exist — on a runner this "
                "usually means the volume is not mounted into the job"
            )
        served = Counter()
        for series_uid in series_uids:
            series_outdir = os.path.join(target_dir, series_uid)
            if os.path.isdir(series_outdir) and not force:
                logger.info(f"{series_outdir} exists, use --force-download to refetch")
                served["already on disk"] += 1
                continue
            served[
                download_series(
                    series_uid, dataset, series_outdir, cache_dir, repo_dirs
                )
            ] += 1
        summary = ", ".join(f"{count} from {label}" for label, count in served.items())
        logger.info(f"collecting {dataset} completed: {summary}")

    elif os.path.isfile(source_file):
        if force or len([f for f in Path(target_dir).glob("**/*.dcm")]) == 0:
            logger.info("downloading files from specified urls")
            download_from_url(target_dir, input_file=str(source_file))
            logger.info("downloading and extracting files completed")
        else:
            logger.info(
                f"dicom files found in {target_dir=}, use --force-download to refetch"
            )
