import subprocess
import os, time
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import zipfile
from io import BytesIO
import re
import glob
from .KaapanaAuth import KaapanaAuth
from .logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)

CWD = os.getcwd()


class DataEndpoints(KaapanaAuth):
    def get_dataset_from_backend(self, dataset):
        r = self.request(
            "kaapana-backend/client/dataset",
            request_type=requests.get,
            params={"name": dataset},
            raise_for_status=False,
        )
        return r.json()

    def check_if_dataset_complete(self, dataset: str, series_uids: list):
        """
        Request the dataset from the kaapana-backend and check if it consists of the the same identifiers as the ids in series_uids.
        Return true if all series are found else false.
        """
        logger.info(f"Check if dataset {dataset} is complete.")
        try:
            backend_dataset = self.get_dataset_from_backend(dataset)
        except:
            logger.warning(
                f"Request to backend failed! Suppose not all series found for dataset {dataset=}."
            )
            return False

        if backend_dataset.get("detail", None) == "Dataset not found":
            return False

        identifiers = backend_dataset.get("identifiers")
        if set(identifiers) == set(series_uids):
            return True
        else:
            logger.warning(f"Dataset not correct: {identifiers=} and {series_uids=}")
            return False

    def wait_for_dataset(self, dataset: str, series_uids: list, max_time=1200):
        """
        Wait until the dataset is completly available in the kaapana-backend.
        """
        start_time = time.time()
        while abs(start_time - time.time()) < max_time:
            time.sleep(5)
            if self.check_if_dataset_complete(dataset=dataset, series_uids=series_uids):
                logger.info(
                    f"All series uids found as identifiers in dataset {dataset}"
                )
            return

        logger.error(f"Waiting for {dataset=} exceeds {max_time=}")
        raise TimeoutError(f"Waiting for {dataset=} exceeds {max_time=}")

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


def send_data_to_platform(dir, host, dataset):
    """
    Send dicom files from directory dir to the host PACS on port 11112 with aetitle aetitle.
    Return a list of send dicoms
    """
    project = "admin"
    report = os.path.join(dir, "report.txt")
    command = f"dcmsend {host} 11112 --scan-directories --call kp-{project} --aetitle kp-{dataset} --create-report-file {report} --scan-pattern *.dcm --recurse {dir}".split()
    logger.info(f"Start sending data to {project=} and dataset {dataset}")
    run = subprocess.run(command)
    try:
        run.check_returncode()
        logger.info(f"Successfully send data with {dataset=}")
    except subprocess.CalledProcessError as e:
        logger.warning(str(e))

        # sys.exit(run.returncode)


def get_series_to_download_from_manifest(file_path):
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
