import os
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.helper import load_workflow_config
from kaapanapy.logger import get_logger
from kaapanapy.settings import OperatorSettings

logger = get_logger(__name__)


def get_data(dcm_uid_object):
    """
    Download series data either from PACS.
    Input:
    :dcm_uid_object: {"dcm-uid": {"series-uid":<series_uid>, "study-uid":<study_uid>, "curated_modality": <curated_modality>}}

    Output:
    (download_successful, series_uid)
    """
    download_successful = False
    dcmweb_helper = HelperDcmWeb()
    series_uid = dcm_uid_object.get("dcm-uid").get("series-uid")
    study_uid = dcm_uid_object.get("dcm-uid").get("study-uid")
    target_dir = make_target_dir_for_series(series_uid=series_uid)
    download_successful = dcmweb_helper.download_series(
        study_uid=study_uid, series_uid=series_uid, target_dir=target_dir
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


def get_identifier_for_model(workflow_config: dict, os_helper: HelperOpensearch):
    """
    Get the series uids as identifier for a model.
    Modelnames are taken from the list at workflow_config["workflow_form"]["tasks"].
    Strings in this list resamble values for the dicom tag "00181030 ProtocolName_keyword.keyword".
    The corresponding identifiers are queries from opensearch.

    """
    project_form = workflow_config.get("project_form")
    opensearch_index = project_form.get("opensearch_index")
    query = {
        "bool": {
            "must": [{"match_all": {}}, {"match_all": {}}],
            "filter": [],
            "should": [],
            "must_not": [],
        }
    }

    if "tasks" in workflow_config["workflow_form"]:
        bool_should = []
        for protocol in workflow_config["workflow_form"]["tasks"]:
            bool_should.append(
                {
                    "match_phrase": {
                        "00181030 ProtocolName_keyword.keyword": {"query": protocol}
                    }
                }
            )
        query["bool"]["must"].append(
            {"bool": {"should": bool_should, "minimum_should_match": 1}}
        )

    query["bool"]["must"].append(
        {"match_phrase": {"00080060 Modality_keyword.keyword": {"query": "OT"}}}
    )
    return os_helper.get_query_dataset(
        index=opensearch_index, query=query, only_uids=True
    )


if __name__ == "__main__":
    workflow_config = load_workflow_config()
    logger.debug("Workflow config loaded.")
    project_form = workflow_config.get("project_form")
    opensearch_index = project_form.get("opensearch_index")
    assert opensearch_index
    os_helper = HelperOpensearch()
    logger.info("Start data download.")
    identifiers = get_identifier_for_model(
        workflow_config=workflow_config, os_helper=os_helper
    )
    dcm_uid_objects = os_helper.get_dcm_uid_objects(
        series_instance_uids=identifiers, index=opensearch_index
    )
    get_data(dcm_uid_object=dcm_uid_objects[0])
