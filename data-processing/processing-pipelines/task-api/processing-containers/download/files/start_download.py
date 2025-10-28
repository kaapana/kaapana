import os
import json
from multiprocessing.pool import ThreadPool
import time
from pathlib import Path
import requests

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


KAAPANA_BACKEND_URL = os.getenv("KAAPANA_BACKEND_URL")


class GetInputOperator:
    def __init__(self):
        self.dcmweb_helper = HelperDcmWeb()
        self.os_helper = HelperOpensearch()
        self.project_index = os.getenv("OPENSEARCH_INDEX")

    def get_data_from_pacs(self, target_dir: str, studyUID: str, seriesUID: str):
        """
        Download the dicom file of a series from a PACS into target_dir
        """
        return self.dcmweb_helper.download_series(
            study_uid=studyUID, series_uid=seriesUID, target_dir=target_dir
        )

    def get_data_from_opensearch(self, target_dir: str, seriesUID: str):
        """
        Download metadata of a series from opensearch and store it as a json file into target_dir
        """
        meta_data = self.os_helper.os_client.get(
            id=seriesUID, index=self.project_index
        )["_source"]
        json_path = os.path.join(target_dir, "metadata.json")
        with open(json_path, "w") as fp:
            json.dump(meta_data, fp, indent=4, sort_keys=True)
        return True

    def get_data(self, dcm_uid_object):
        """
        Download series data either from PACS or from Opensearch based on the workflow_config.

        Input:
        :dcm_uid_object: {"dcm-uid": {"series-uid":<series_uid>, "study-uid":<study_uid>, "curated_modality": <curated_modality>}}

        Output:
        (download_successful, series_uid)
        """
        download_successful = False
        data_source = os.getenv("SOURCE")

        series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
        study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
        target_dir = Path(f"/home/kaapana/downloads/{series_uid}")

        if data_source.lower() == "opensearch":
            download_successful = self.get_data_from_opensearch(
                target_dir=target_dir, seriesUID=series_uid
            )
        elif data_source.lower() == "pacs":
            download_successful = self.get_data_from_pacs(
                target_dir=target_dir, studyUID=study_uid, seriesUID=series_uid
            )
        else:
            raise NotImplementedError(
                f"{data_source=} not supported! Must be one of ['opensearch','pacs']"
            )

        return download_successful, series_uid

    def get_identifiers(self, dataset: str):
        """
        Return a list of identifiers for the dataset.
        """
        access_token = get_project_user_access_token()
        r = requests.get(
            f"{KAAPANA_BACKEND_URL}/client/dataset",
            params={"name": dataset},
            verify=False,
            headers={"Authorization": f"Bearer {access_token}"},
            cookies={
                "Project": json.dumps(
                    {
                        "name": "admin",
                        "id": "cd98d3b5-6e15-44d9-80d8-53bc8523d063",
                    }
                )
            },
        )

        print()
        print(r)
        print(r.text)
        print()

        r.raise_for_status()
        return r.json().get("identifiers")

    def download_data_for_workflow(self):
        """
        Download data from the PACS or opensearch into the output directory of the operator.
        """
        dataset = os.getenv("DATASET")
        identifiers = self.get_identifiers(dataset=dataset)
        parallel_downloads = os.getenv("PARALLEL_DOWNLOADS")

        dcm_uid_objects = self.os_helper.get_dcm_uid_objects(
            series_instance_uids=identifiers,
            index=self.project_index,
        )

        if len(dcm_uid_objects) == 0:
            logger.error(
                f"No metadata found in {self.project_index=} for {identifiers=}"
            )
            raise ValueError(
                f"No metadata found in {self.project_index=} for {identifiers=}"
            )

        series_download_fail = []
        num_done = 0
        num_total = len(dcm_uid_objects)
        time_start = time.time()

        with ThreadPool(parallel_downloads) as threadpool:
            results = threadpool.imap_unordered(self.get_data, dcm_uid_objects)
            for download_successful, series_uid in results:
                if not download_successful:
                    series_download_fail.append(series_uid)
                num_done += 1
                if num_done % 10 == 0:
                    time_elapsed = time.time() - time_start
                    logger.info(f"{num_done}/{num_total} done")
                    logger.info(
                        "Time elapsed: %d:%02d minutes" % divmod(time_elapsed, 60)
                    )
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


if __name__ == "__main__":
    logger.info("Start GetInputOperator.")
    ### This helper is used in get_data_from_pacs()
    logger.info("Start data download.")
    logger.info("Continue")

    operator = GetInputOperator()
    operator.download_data_for_workflow()
