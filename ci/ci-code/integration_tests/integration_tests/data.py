import glob
import json
import logging
import os
import shutil
import re
import subprocess
import time
import uuid
import zipfile
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


def download_from_tcia(outdir, series_uid):
    """
    Fetch one series from TCIA into `outdir/series_uid`.

    Raises SeriesUnavailable after TCIA_ATTEMPTS failed tries.
    """
    series_outdir = os.path.join(outdir, series_uid)
    last_error = None
    for attempt in range(1, TCIA_ATTEMPTS + 1):
        try:
            r = requests.get(
                TCIA_GETIMAGE_URL,
                params={"SeriesInstanceUID": series_uid},
                timeout=TCIA_TIMEOUT,
            )
            r.raise_for_status()
            zipfile.ZipFile(BytesIO(r.content)).extractall(series_outdir)
            return
        except (requests.RequestException, zipfile.BadZipFile, OSError) as error:
            last_error = error
            logger.warning(
                f"TCIA attempt {attempt}/{TCIA_ATTEMPTS} for {series_uid} failed: {error}"
            )
    raise SeriesUnavailable(f"TCIA did not deliver {series_uid}: {last_error}")


def download_from_repo(
    repo_dir: str, dataset: str, series_uid: str, series_outdir: str
):
    """
    Take one series from `<repo_dir>/<dataset>/<uid>.zip`.

    The zip holds what TCIA's getImage returns.
    """
    archive = Path(repo_dir) / dataset / f"{series_uid}.zip"
    if not archive.is_file():
        raise SeriesUnavailable(f"{archive} does not exist")
    try:
        with zipfile.ZipFile(archive) as content:
            content.extractall(os.path.join(series_outdir, series_uid))
    except (zipfile.BadZipFile, OSError) as error:
        raise SeriesUnavailable(f"Unpacking {archive} failed: {error}") from error


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
    """
    Shallow sparse clone of one test-data repository, `entry` being
    {url, token, ref, path}. Returns the directory holding the series zips.

    An existing `dest` is reused. Every xdist worker calls this, so the clone
    goes to a private directory and is moved into place with one rename.
    """
    url, token = entry["url"], entry.get("token", "")
    ref = entry.get("ref", "main")
    path = entry.get("path", "ci_integration_tests")
    if dest.is_dir():
        return dest / path

    authed = url.replace("https://", f"https://oauth2:{token}@", 1) if token else url
    env = {**os.environ, "GIT_LFS_SKIP_SMUDGE": "1", "GIT_TERMINAL_PROMPT": "0"}
    # Unique per attempt: the root can be a volume shared by several job
    # containers, and each container's PID namespace starts over at low
    # numbers, so a pid alone is not unique there.
    staging = dest.with_name(f"{dest.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}")
    shutil.rmtree(staging, ignore_errors=True)
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
            ref,
            authed,
            str(staging),
        ],
        ["git", "-C", str(staging), "sparse-checkout", "set", path],
    ):
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        if result.returncode != 0:
            # The clone url carries the token, keep it out of the CI log.
            shutil.rmtree(staging, ignore_errors=True)
            # git echoes the clone url, which carries the token.
            message = result.stderr.strip().replace(authed, url)
            raise SeriesUnavailable(
                message.replace(token, "***") if len(token) >= 8 else message
            )

    # The clone url carries the token and git keeps it in .git/config. The
    # destination is a volume every job on this runner can read, so drop the
    # credential before publishing the directory. Nothing fetches afterwards.
    subprocess.run(
        ["git", "-C", str(staging), "remote", "set-url", "origin", url],
        capture_output=True,
        text=True,
    )

    try:
        os.rename(staging, dest)
    except OSError:
        # Another worker got there first, its clone is the one to use.
        shutil.rmtree(staging, ignore_errors=True)
    return dest / path


def clone_test_data_repos(spec: str, dest_root: Path) -> list:
    """
    Clone every repository in `spec`, a JSON array of {url, token, ref, path}
    or a path to a file holding one. A repository that fails is skipped.
    """
    if os.path.isfile(spec):
        spec = Path(spec).read_text()
    try:
        entries = json.loads(spec)
    except json.JSONDecodeError as error:
        logger.warning(
            f"Test-data repositories are not valid JSON, ignoring them: {error}"
        )
        return []

    dirs = []
    for n, entry in enumerate(entries, start=1):
        try:
            repo_dir = clone_test_data_repo(
                entry, Path(dest_root) / f"test_data_repo_{n}"
            )
        except (SeriesUnavailable, KeyError, OSError) as error:
            logger.warning(f"Repository {n} ({entry.get('url')}) not cloned: {error}")
            continue
        logger.info(
            f"Cloned repository {n} to {repo_dir}, {len(list(repo_dir.glob('**/*.zip')))} series archives."
        )
        dirs.append(str(repo_dir))
    return dirs


def download_series(series_uid: str, dataset: str, series_outdir: str, repo_dirs=None):
    """
    Get one series, trying the repositories first and TCIA last.

    Raises SeriesUnavailable if every source fails.
    """
    sources = [
        (
            f"repo{n} ({repo_dir})",
            lambda d=repo_dir: download_from_repo(
                d, dataset, series_uid, series_outdir
            ),
        )
        for n, repo_dir in enumerate(repo_dirs or [], start=1)
    ]
    sources.append(("tcia", lambda: download_from_tcia(series_outdir, series_uid)))

    failures = []
    for label, fetch in sources:
        try:
            fetch()
            if failures:
                logger.info(
                    f"Got {series_uid} from {label} after {len(failures)} source(s) failed."
                )
            return
        except SeriesUnavailable as error:
            failures.append(f"{label}: {error}")
            logger.warning(f"{label} could not deliver {series_uid}: {error}")

    raise SeriesUnavailable(
        f"{series_uid} unavailable from all {len(failures)} source(s) -> "
        + " | ".join(failures)
    )


def download_data(source_file: Path, target_dir: Path, force=False, repo_dirs=None):
    """
    Download data either from tcia or from from an url.
    File contains either a tcia manifest or a download url.
    The data is downloaded into target_dir.
    Parameter force determines, whether to force download, even if the directories per series already exist.
    repo_dirs holds the test-data repositories, see download_series().
    """
    repo_dirs = list(repo_dirs or [])
    if str(source_file).endswith(".tcia"):
        series_uids = get_series_to_download_from_manifest(source_file)
        dataset = Path(target_dir).name
        logger.info(
            f"Collecting {dataset}: {len(series_uids)} series from {len(repo_dirs)} repository(ies), TCIA last."
        )
        if not repo_dirs:
            logger.warning(
                "No test-data repository configured, TCIA is the only source."
            )
        for series_uid in series_uids:
            series_outdir = os.path.join(target_dir, series_uid)
            if os.path.isdir(series_outdir) and not force:
                logger.info(
                    f"Directory {series_outdir} already exists -> Use --force_download to download anyway."
                )
                continue
            download_series(series_uid, dataset, series_outdir, repo_dirs)
        logger.info(f"Collecting {dataset} completed.")

    elif os.path.isfile(source_file):
        if force or len([f for f in Path(target_dir).glob("**/*.dcm")]) == 0:
            logger.info("Downloading files from specified urls")
            download_from_url(target_dir, input_file=str(source_file))
            logger.info("Downloading and extracting files completed.")
        else:
            logger.info(
                f"Dicom files found in {target_dir=}. Skip download. Use --force to force download."
            )
