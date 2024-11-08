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


def check_modality_of_workflow(modality: str):
    """
    Check if the modality specified in the workflow_form of the workflow matches the modality.

    :dag_config: Config dictionary of a workflow.
    :modality: Modality to compare against the workflow_form in workflow_config.
    """
    workflow_config = load_workflow_config()
    workflow_modality = workflow_config.get("workflow_form").get("input")
    if not type(workflow_modality) == str:
        raise TypeError(
            f"{workflow_modality=} has not the expected type of str. {workflow_config=}"
        )
    valid_modalities = workflow_modality.lower().split(",")

    if modality.lower() not in valid_modalities:
        raise ValueError(
            f"Data modality {modality.lower()} is not one of {valid_modalities=}"
        )


def get_data_from_pacs(target_dir: str, studyUID: str, seriesUID: str):
    """
    Download the dicom file of a series from a PACS into target_dir
    """
    return dcmweb_helper.download_series(
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
    return True


def get_data(dcm_uid_object):
    """
    Download series data either from PACS or from Opensearch based on the workflow_config.

    Input:
    :dcm_uid_object: {"dcm-uid": {"series-uid":<series_uid>, "study-uid":<study_uid>, "curated_modality": <curated_modality>}}

    Output:
    (download_successful, series_uid)
    """
    download_successful = False
    operator_arguments = GetInputArguments()
    data_type = operator_arguments.data_type

    if operator_arguments.check_modality:
        modality = dcm_uid_object.get("dcm-uid").get("curated_modality")
        check_modality_of_workflow(modality)

    series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
    study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
    target_dir = make_target_dir_for_series(series_uid=series_uid)

    if data_type == "json":
        download_successful = get_data_from_opensearch(
            target_dir=target_dir, seriesUID=series_uid
        )
    elif data_type == "dicom":
        download_successful = get_data_from_pacs(
            target_dir=target_dir, studyUID=study_uid, seriesUID=series_uid
        )
    else:
        raise NotImplementedError(
            f"{data_type=} not supported! Must be one of ['json','dicom']"
        )

    return download_successful, series_uid


def make_target_dir_for_series(series_uid: str):
    """
    Create the target directory for a series object
    """
    settings = OperatorSettings()
    target_dir = os.path.join(
        settings.workflow_dir,
        settings.batch_name,
        series_uid,
        settings.operator_out_dir,
    )
    os.makedirs(target_dir, exist_ok=True)
    return target_dir


def download_data_for_workflow(workflow_config):
    """
    Download data from the PACS or opensearch into the output directory of the operator.
    """
    settings = OperatorSettings()
    operator_arguments = GetInputArguments()
    logger.debug(f"{settings=}")
    logger.debug(f"{operator_arguments=}")

    identifiers = workflow_config.get("data_form").get("identifiers")
    parallel_downloads = operator_arguments.parallel_downloads

    # set include and exclude tags from respective workflow form keys
    include_custom_tag=""
    exclude_custom_tag=""
    if operator_arguments.include_custom_tag_property != "":
        include_custom_tag = workflow_config.get("workflow_form").get(operator_arguments.include_custom_tag_property)
    if operator_arguments.exclude_custom_tag_property != "":
        exclude_custom_tag = workflow_config.get("workflow_form").get(operator_arguments.exclude_custom_tag_property)

    dcm_uid_objects = HelperOpensearch.get_dcm_uid_objects(
        identifiers,
        include_custom_tag=include_custom_tag,
        exclude_custom_tag=exclude_custom_tag,
    )

    dataset_limit = workflow_config.get("data_form").get("dataset_limit")
    if workflow_config.get("data_form").get("dataset_limit"):
        dcm_uid_objects = dcm_uid_objects[:dataset_limit]

    series_download_fail = []
    num_done = 0
    num_total = len(dcm_uid_objects)
    time_start = time.time()

    with ThreadPool(parallel_downloads) as threadpool:
        results = threadpool.imap_unordered(get_data, dcm_uid_objects)
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


if __name__ == "__main__":
    logger.info("Start GetInputOperator.")
    ### This helper is used in get_data_from_pacs()
    dcmweb_helper = HelperDcmWeb()
    logger.debug("HelperDcmWeb object initialized.")
    workflow_config = load_workflow_config()
    logger.debug("Workflow config loaded.")

    ### Overwrite HelperOpenseach index to be the project specific index
    project_form = workflow_config.get("project_form")
    HelperOpensearch.index = project_form.get("opensearch_index")
    assert HelperOpensearch.index
    logger.info("Start data download.")
    download_data_for_workflow(workflow_config)
