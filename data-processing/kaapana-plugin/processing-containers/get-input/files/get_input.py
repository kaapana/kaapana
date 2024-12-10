from pydantic_settings import BaseSettings
from pydantic import Field
import os
import json
from multiprocessing.pool import ThreadPool
import time

from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.settings import OperatorSettings

logger = get_logger(__name__)


class GetInputArguments(BaseSettings):
    data_type: str = Field("dicom")
    include_custom_tag_property: str = ""
    exclude_custom_tag_property: str = ""
    batch_name: str = "batch"
    check_modality: bool = False
    parallel_downloads: int = 3


class GetInputOperator:
    def __init__(self):
        self.workflow_config = load_workflow_config()
        self.dcmweb_helper = HelperDcmWeb()
        self.os_helper = HelperOpensearch()
        self.project_form = self.workflow_config.get("project_form")
        self.project_index = self.project_form.get("opensearch_index")
        self.operator_settings = OperatorSettings()
        self.operator_arguments = GetInputArguments()
        logger.debug(f"{self.operator_arguments=}")
        logger.debug(f"{self.workflow_config=}")

    def check_modality_of_workflow(self, modality: str):
        """
        Check if the modality specified in the workflow_form of the workflow matches the modality.

        :dag_config: Config dictionary of a workflow.
        :modality: Modality to compare against the workflow_form in workflow_config.
        """
        workflow_modality = self.workflow_config.get("workflow_form").get("input")
        if not type(workflow_modality) == str:
            raise TypeError(
                f"{workflow_modality=} has not the expected type of str. {self.workflow_config=}"
            )
        valid_modalities = workflow_modality.lower().split(",")

        if modality.lower() not in valid_modalities:
            raise ValueError(
                f"Data modality {modality.lower()} is not one of {valid_modalities=}"
            )

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
        data_type = self.operator_arguments.data_type

        if self.operator_arguments.check_modality:
            modality = dcm_uid_object.get("dcm-uid").get("curated_modality")
            self.check_modality_of_workflow(modality)

        series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
        study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
        target_dir = self.make_target_dir_for_series(series_uid=series_uid)

        if data_type == "json":
            download_successful = self.get_data_from_opensearch(
                target_dir=target_dir, seriesUID=series_uid
            )
        elif data_type == "dicom":
            download_successful = self.get_data_from_pacs(
                target_dir=target_dir, studyUID=study_uid, seriesUID=series_uid
            )
        else:
            raise NotImplementedError(
                f"{data_type=} not supported! Must be one of ['json','dicom']"
            )

        return download_successful, series_uid

    def make_target_dir_for_series(self, series_uid: str):
        """
        Create the target directory for a series object
        """
        target_dir = os.path.join(
            self.operator_settings.workflow_dir,
            self.operator_settings.batch_name,
            series_uid,
            self.operator_settings.operator_out_dir,
        )
        os.makedirs(target_dir, exist_ok=True)
        return target_dir

    def download_data_for_workflow(self):
        """
        Download data from the PACS or opensearch into the output directory of the operator.
        """
        identifiers = self.workflow_config.get("data_form").get("identifiers")
        parallel_downloads = self.operator_arguments.parallel_downloads

        # set include and exclude tags from respective workflow form keys
        include_custom_tag = ""
        exclude_custom_tag = ""
        if self.operator_arguments.include_custom_tag_property != "":
            include_custom_tag = self.workflow_config.get("workflow_form").get(
                self.operator_arguments.include_custom_tag_property
            )
        if self.operator_arguments.exclude_custom_tag_property != "":
            exclude_custom_tag = self.workflow_config.get("workflow_form").get(
                self.operator_arguments.exclude_custom_tag_property
            )

        dcm_uid_objects = self.os_helper.get_dcm_uid_objects(
            series_instance_uids=identifiers,
            include_custom_tag=include_custom_tag,
            exclude_custom_tag=exclude_custom_tag,
            index=self.project_index,
        )

        dataset_limit = self.workflow_config.get("data_form").get("dataset_limit")
        if self.workflow_config.get("data_form").get("dataset_limit"):
            dcm_uid_objects = dcm_uid_objects[:dataset_limit]

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
    operator = GetInputOperator()
    operator.download_data_for_workflow()
