import subprocess
import os, sys, time
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
TEST_DATA = [
    {
        "aet": "test-CT",
        "destination": os.path.join(CWD, "../jobs/testdata/data/ct/"),
        "input": os.path.join(CWD, "../jobs/testdata/download-info/ct-manifest.tcia"),
    },
    {
        "aet": "test-DELETE",
        "destination": os.path.join(CWD, "../jobs/testdata/data/deletion/"),
        "input": os.path.join(
            CWD, "../jobs/testdata/download-info/deletion-manifest.tcia"
        ),
    },
    {
        "aet": "test-SEG",
        "destination": os.path.join(CWD, "../jobs/testdata/data/seg/"),
        "input": os.path.join(CWD, "../jobs/testdata/download-info/seg-url.url"),
    },
    {
        "aet": "test-MRT",
        "destination": os.path.join(CWD, "../jobs/testdata/data/mrt/"),
        "input": os.path.join(CWD, "../jobs/testdata/download-info/mrt-manifest.tcia"),
    },
    {
        "aet": "test-MODELS",
        "destination": os.path.join(CWD, "../jobs/testdata/data/models/"),
        "input": os.path.join(CWD, "../jobs/testdata/download-info/models-url.url"),
    },
]


class DataEndpoints(KaapanaAuth):
    def get_dataset_from_backend(self, dataset):
        r = self.request(
            "kaapana-backend/client/dataset",
            request_type=requests.get,
            params={"name": dataset},
            raise_for_status=False,
        )
        return r.json()

    def check_if_dataset_complete(self, test_set: dir):
        """
        Check for test_set if for every directory the corresponding series is listed as an identifier in the dataset with name aet
        Return true if all series are found else false
        """
        return_value = True
        aetitle = test_set.get("aet")
        logger.info(f"Check if dataset {aetitle} is complete.")
        try:
            dataset = self.get_dataset_from_backend(aetitle)
        except:
            logger.warning(
                f"Request to backend failed! Suppose not all series found for dataset {aetitle=}."
            )
            return False
        if dataset.get("detail", None) == "Dataset not found":
            return False
        identifiers = dataset.get("identifiers")
        data_dir = test_set.get("destination")
        series_to_find = list_of_series_in_dir(data_dir)
        for series_uid in series_to_find:
            if series_uid not in identifiers:
                logger.warning(f"{series_uid=} not found in {dataset=}")
                return_value = False
        if len(identifiers) != len(series_to_find):
            return_value = False
            logger.warning(f"Sizes don't match: {identifiers=} and {series_to_find=} ")
        return return_value

    def check_all_datasets_in_backend(self, max_time=1200):
        """
        Check for all elements in TEST_DATA  if for every directory the corresponding series is listed as an identifier in the dataset with name aet
        Return true if all series are found else false
        """
        start_time = time.time()
        unchecked_cohorts = [dataset.get("aet") for dataset in TEST_DATA]
        while abs(start_time - time.time()) < max_time and len(unchecked_cohorts) > 0:
            time.sleep(5)
            for testdata in TEST_DATA:
                aet = testdata.get("aet")
                if (
                    aet in unchecked_cohorts
                    and (check := self.check_if_dataset_complete(testdata))
                    and check == True
                ):
                    unchecked_cohorts.remove(aet)
                    logger.info(
                        f"All series uids found as identifiers in dataset {aet}"
                    )
        for aet in unchecked_cohorts:
            logger.error(f"Dataset {aet} not correctly created!")
        if abs(start_time - time.time()) > max_time:
            logger.error(f"Waiting for datasets exceeds {max_time=}")
            sys.exit
        if len(unchecked_cohorts) > 0:
            sys.exit(1)

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


def send_data_to_platform(dir, host, aetitle):
    """
    Send dicom files from directory dir to the host PACS on port 11112 with aetitle aetitle.
    Return a list of send dicoms
    """
    project = "admin"
    report = os.path.join(dir, "report.txt")
    command = f"dcmsend {host} 11112 --scan-directories --call kp-{project} --aetitle kp-{aetitle} --create-report-file {report} --scan-pattern *.dcm --recurse {dir}".split()
    logger.info(f"Start sending data to {project=} and dataset {aetitle}")
    run = subprocess.run(command)
    try:
        run.check_returncode()
        logger.info(f"Successfully send data with {aetitle=}")
    except subprocess.CalledProcessError as e:
        sys.exit(run.returncode)


def get_series_to_download_from_manifest(file_path):
    regex = re.compile(r"[0-9\.]*")
    series_uids = []
    with open(file_path, "r") as f:
        for line in f:
            if (uid := regex.match(line)) and (uid.group() != ""):
                series_uids.append(uid.group())
    return series_uids


def download_from_url(dir, input_file="download-urls.txt"):
    """
    Download files from urls specified in `dir/download-urls.txt`, save into `output` and unzip `output`.
    """
    file = os.path.join(dir, input_file)
    with open(file, "r") as f:
        for url in f:
            r = requests.get(url)
            content = zipfile.ZipFile(BytesIO(r.content))
            content.extractall(dir)


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
