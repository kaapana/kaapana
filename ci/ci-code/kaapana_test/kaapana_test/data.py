import glob
import logging
import os
import re
import subprocess
import time
import zipfile
from io import BytesIO
from pathlib import Path

import requests
from kaapana_test.utils.KaapanaAuth import KaapanaAuth
from kaapana_test.utils.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


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

    def wait_for_dataset(self, source_file: Path, kaapana_dataset: str, max_time=1200):
        """
        Wait until the dataset is completly available in the kaapana-backend.
        """
        series_uids = get_series_to_download_from_manifest(source_file)
        start_time = time.time()
        while abs(start_time - time.time()) < max_time:
            time.sleep(5)
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
            r = requests.get(url)
            content = zipfile.ZipFile(BytesIO(r.content))
            content.extractall(output_dir)


def download_from_tcia(outdir, series_uid):
    series_outdir = os.path.join(outdir, series_uid)
    r = requests.get(
        "https://services.cancerimagingarchive.net/nbia-api/services/v1/getImage?SeriesInstanceUID={}".format(
            series_uid
        )
    )
    content = zipfile.ZipFile(BytesIO(r.content))
    content.extractall(series_outdir)


def list_of_series_in_dir(dir):
    list_of_series = []
    dicom_files = glob.glob(os.path.join(dir, "**/*.dcm"), recursive=True)
    for file in dicom_files:
        if (
            series_uid := os.path.dirname(file).split("/")[-1]
        ) and series_uid not in list_of_series:
            list_of_series.append(series_uid)
    return list_of_series


def download_data(source_file: Path, target_dir: Path, force=False):
    """
    Download data either from tcia or from from an url.
    File contains either a tcia manifest or a download url.
    The data is downloaded into target_dir.
    Parameter force determines, whether to force download, even if the directories per series already exist.
    """
    if str(source_file).endswith(".tcia"):
        series_uids = get_series_to_download_from_manifest(source_file)
        logger.info("Starting to download and extract .dcm files from TCIA.")
        for series_uid in series_uids:
            series_outdir = os.path.join(target_dir, series_uid)
            if os.path.isdir(series_outdir) and not force:
                logger.info(
                    f"Directory {series_outdir} already exists -> Use --force_download to download anyway."
                )
                continue
            download_from_tcia(series_outdir, series_uid)
            logger.info("Downloading files ...")
        logger.info("Downloading files from TCIA completed.")

    elif os.path.isfile(source_file):
        if force or len([f for f in Path(target_dir).glob("**/*.dcm")]) == 0:
            logger.info("Downloading files from specified urls")
            download_from_url(target_dir, input_file=str(source_file))
            logger.info("Downloading and extracting files completed.")
        else:
            logger.info(
                f"Dicom files found in {target_dir=}. Skip download. Use --force to force download."
            )
