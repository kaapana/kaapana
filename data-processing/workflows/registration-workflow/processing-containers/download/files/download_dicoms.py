import os
import json
from multiprocessing.pool import ThreadPool
import time
from pathlib import Path
import requests

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.logger import get_logger

import argparse

logger = get_logger(__name__)


def get_project(identifier: str, aii_root_url: str):
    r = requests.get(f"{aii_root_url}/projects/{identifier}")
    r.raise_for_status()
    return r.json()


def get_identifiers(project: dict, dataset: str, kaapana_backend_root_url: str):
    """
    Return a list of identifiers for the dataset.
    """
    r = requests.get(
        f"{kaapana_backend_root_url}/client/dataset",
        params={"name": dataset},
        verify=False,
        headers={"Project": json.dumps(project)},
    )

    r.raise_for_status()
    return r.json().get("identifiers")


def get_dcm_uid_objcets(identifiers, opensearch_index):
    os_helper = HelperOpensearch()
    dcm_uid_objects = os_helper.get_dcm_uid_objects(
        series_instance_uids=identifiers,
        index=opensearch_index,
    )
    if len(dcm_uid_objects) == 0:
        logger.error(f"No metadata found in {opensearch_index=} for {identifiers=}")
        raise ValueError(f"No metadata found in {opensearch_index=} for {identifiers=}")

    return dcm_uid_objects


def download_dicom_series(dcm_uid_objects: dict, parallel_downloads: int, output: Path):
    """
    Download data from the PACS or opensearch into the output directory of the operator.
    """
    dcmweb_helper = HelperDcmWeb()

    series_download_fail = []
    num_done = 0
    num_total = len(dcm_uid_objects)
    time_start = time.time()

    def download_series(dcm_uid_object):
        download_successful = False
        study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
        series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
        target_dir = Path(output, series_uid)
        download_successful = dcmweb_helper.download_series(
            study_uid=study_uid, series_uid=series_uid, target_dir=target_dir
        )
        return download_successful, series_uid

    with ThreadPool(parallel_downloads) as threadpool:
        results = threadpool.imap_unordered(download_series, dcm_uid_objects)
        for download_successful, series_uid in results:
            if not download_successful:
                series_download_fail.append(series_uid)
            num_done += 1
            if num_done % 10 == 0:
                time_elapsed = time.time() - time_start
                logger.info(f"{num_done}/{num_total} done")
                logger.info("Time elapsed: %d:%02d minutes" % divmod(time_elapsed, 60))
                logger.info(
                    "Estimated time remaining: %d:%02d minutes"
                    % divmod(time_elapsed / num_done * (num_total - num_done), 60)
                )
                logger.info("Series per second: %.2f" % (num_done / time_elapsed))
    if len(series_download_fail) > 0:
        raise Exception(
            "Some series could not be downloaded: {}".format(series_download_fail)
        )
    logger.info("All series downloaded successfully")


def parse_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--dataset", type=str, default=os.getenv("DATASET"))
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output directory.",
        default="/home/kaapana/downloads",
    )
    parser.add_argument(
        "-n",
        "--number-parallel-downloads",
        type=int,
        help="Number of parallel threads to download items in the dataset.",
        default=int(os.getenv("PARALLEL_DOWNLOADS")),
    )
    parser.add_argument(
        "-p",
        "--project",
        type=str,
        help="Project identifier",
        default=os.getenv("KAAPANA_PROJECT_IDENTIFIER"),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    project = get_project(
        identifier=args.project, aii_root_url=os.getenv("KAAPANA_AII_URL")
    )

    identifiers = get_identifiers(
        project=project,
        dataset=args.dataset,
        kaapana_backend_root_url=os.getenv("KAAPANA_BACKEND_URL"),
    )

    dcm_uid_objects = get_dcm_uid_objcets(
        identifiers=identifiers, opensearch_index=project.get("opensearch_index")
    )

    download_dicom_series(
        dcm_uid_objects=dcm_uid_objects,
        parallel_downloads=args.number_parallel_downloads,
        output=args.output,
    )
