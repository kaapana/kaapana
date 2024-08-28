from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os
import json

from HelperDcmWeb import HelperDcmWeb
from HelperOpensearch import HelperOpensearch
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger

logger = get_logger(__name__)


class OperatorSettings(BaseSettings):
    run_id: str
    dag_id: str
    workflow_dir: str
    batch_name: str = "batch"
    workflow_name: str
    operator_out_dir: str
    batches_input_dir: str

    operator_in_dir: Optional[str] = None


class GetInputArguments(BaseSettings):
    data_type: str = Field("dicom")
    include_custom_tag: str = ""
    exclude_custom_tag: str = ""
    batch_name: str = "batch"
    check_modality: bool = False


def load_workflow_config():
    """
    Load and return the workflow config.
    """
    settings = OperatorSettings()
    config_path = os.path.join(settings.workflow_dir, "conf", "conf.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config


def check_modality_of_workflow(workflow_config: dict, modality: str):
    """
    Check if the modality specified in the workflow_form of the workflow matches the modality.

    :dag_config: Config dictionary of a workflow.
    :modality: Modality to compare against the workflow_form in workflow_config.
    """
    workflow_modality = workflow_config.get("workflow_form").get("input")
    assert workflow_modality.lower() == modality.lower()


def get_data_from_pacs(target_dir: str, studyUID: str, seriesUID: str):
    """
    Download the dicom file of a series from a PACS into target_dir
    """
    dcmweb_helper.download_series(
        study_uid=studyUID, series_uid=seriesUID, target_dir=target_dir
    )


def get_data_from_opensearch(target_dir: str, seriesUID: str):
    """
    Download metadata of a series from opensearch and store it as a json file into target_dir
    """
    meta_data = HelperOpensearch.get_series_metadata(series_instance_uid=seriesUID)
    json_path = os.path.join(target_dir, "metadata.json")
    with open(json_path, "w") as fp:
        json.dump(meta_data, fp, indent=4, sort_keys=True)


def download_data_for_workflow(workflow_config):
    """
    Download data from the PACS or opensearch into the output directory of the operator.
    """
    settings = OperatorSettings()
    operator_arguments = GetInputArguments()
    logger.debug(f"{settings=}")
    logger.debug(f"{operator_arguments=}")

    identifiers = workflow_config.get("data_form").get("identifiers")
    data_type = operator_arguments.data_type

    dcm_uid_objects = HelperOpensearch.get_dcm_uid_objects(
        identifiers,
        include_custom_tag=operator_arguments.include_custom_tag,
        exclude_custom_tag=operator_arguments.exclude_custom_tag,
    )

    for dcm_uid_object in dcm_uid_objects:
        logger.debug(f"Start download of {dcm_uid_object=}")
        ### Check if the modality of the series matches the
        modality = dcm_uid_object.get("dcm-uid").get("curated_modality")
        if operator_arguments.check_modality:
            check_modality_of_workflow(workflow_config, modality)

        series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
        study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
        target_dir = os.path.join(
            settings.workflow_dir,
            settings.batch_name,
            series_uid,
            settings.operator_out_dir,
        )
        os.makedirs(target_dir, exist_ok=True)
        if data_type == "json":
            get_data_from_opensearch(target_dir=target_dir, seriesUID=series_uid)
        elif data_type == "dicom":
            get_data_from_pacs(
                target_dir=target_dir, studyUID=study_uid, seriesUID=series_uid
            )
        else:
            raise NotImplementedError(
                f"{data_type=} not supported! Must be one of ['json','dicom']"
            )


if __name__ == "__main__":
    logger.info("Start GetInputOperator.")
    dcmweb_helper = HelperDcmWeb(access_token=get_project_user_access_token())
    logger.debug("HelperDcmWeb object initialized.")
    workflow_config = load_workflow_config()
    logger.debug("Workflow config loaded.")
    logger.info("Start data download.")
    download_data_for_workflow(workflow_config)
