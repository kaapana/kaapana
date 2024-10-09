import base64
import json
import logging
import os
from typing import Any, Dict
from pydantic_settings import BaseSettings
from pydantic import Field

from external_pacs.HelperDcmWebEndpointsManager import HelperDcmWebEndpointsManager
from external_pacs.utils import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.settings import OperatorSettings
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

    
class GetInputArguments(BaseSettings):
    action: str = Field("add")
    dataset_name: str = "external_data"
    


def decode_service_account_info(encoded_info: str) -> Dict[str, Any]:
    """
    Decode the base64-encoded service account information.

    :param encoded_info: The base64-encoded service account info string.
    :return: A dictionary containing the decoded service account information.
    """
    decoded_bytes = base64.b64decode(encoded_info)
    decoded_string = decoded_bytes.decode("utf-8")
    return json.loads(decoded_string)


def filter_series_to_import(metadata, external_series_uids):
    """
    Filter out series that are already imported based on the local database.

    :param metadata: The metadata containing series information.
    :param external_series_uids: The list of external series UIDs to compare against.
    :return: A list of metadata instances for series that need to be imported.
    """
    def extract_series_uid(instance):
        return instance.get("0020000E", {"Value": [None]})["Value"][0]

    local_series_uids = set(
        map(
            lambda result: result["dcm-uid"]["series-uid"],
            HelperOpensearch.get_dcm_uid_objects(series_instance_uids=external_series_uids),
        )
    )
    filtered_series = [
        instance for instance in metadata
        if extract_series_uid(instance) not in local_series_uids
    ]
    logger.info(
        f"{len(filtered_series)} new series imported from {len(external_series_uids)}"
    )
    return filtered_series


def download_external_metadata(dcmweb_endpoint: str, ae_title: str, service_account_info: Dict[str, Any], operator_out_dir: str, dag_run_id: str):
    """
    Download metadata for series from the external DICOM web service and save it to the specified directory.

    :param dcmweb_endpoint: The endpoint of the external DICOM web service.
    :param ae_title: The AE title to associate with the metadata.
    :param service_account_info: The service account information for authentication.
    :param operator_out_dir: The base output directory for the operator.
    :param dag_run_id: The unique identifier for the current DAG run.
    """
    logger.info(f"Adding external metadata: {dcmweb_endpoint}")
    dcmweb_helper = get_dcmweb_helper(
        dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
    )
    metadata = dcmweb_helper.search_for_instances()

    if not metadata:
        logger.error("No metadata found.")
        exit(1)
    logger.info(f"Found {len(metadata)} series")

    external_series_uids = list(set(map(lambda inst: inst.get("0020000E", {"Value": [None]})["Value"][0], metadata)))
    metadata = filter_series_to_import(metadata, external_series_uids)

    for instance in metadata:
        series_uid = instance.get("0020000E", {"Value": [None]})["Value"][0]
        if not series_uid:
            raise KeyError(f"Required field missing: Series UID (0020000E) in the series {instance}")

        target_dir = os.path.join(
            operator_out_dir,
            dag_run_id,
            "batch",
            series_uid,
        )

        os.makedirs(target_dir, exist_ok=True)
        json_path = os.path.join(target_dir, "metadata.json")

        instance["00020026"] = {"vr": "UR", "Value": [dcmweb_endpoint]}
        instance["00120020"] = {"vr": "LO", "Value": [ae_title]}

        with open(json_path, "w", encoding="utf8") as fp:
            json.dump(instance, fp, indent=4, sort_keys=True)


def manage_secret(action: str, dcmweb_endpoint: str, service_account_info: Dict[str, Any] = None):
    """
    Manage the creation or deletion of a Kubernetes secret for the DICOM web service.

    :param action: The action to perform ('add' or 'delete').
    :param dcmweb_endpoint: The endpoint of the external DICOM web service.
    :param service_account_info: The service account information for creating a secret (only required for 'add').
    """
    secret_name = hash_secret_name(name=dcmweb_endpoint)

    if action == "add":
        if not service_account_info:
            logger.error("Service account info must be provided for adding a secret.")
            return

        create_k8s_secret(secret_name=secret_name, secret_data=service_account_info)
        logger.info("Secret successfully saved.")
    elif action == "delete":
        secret = get_k8s_secret(secret_name=secret_name)
        if not secret:
            logger.error("No secret to remove, can't remove.")
            return
        delete_k8s_secret(secret_name)
        logger.info("Secret successfully removed.")


def delete_from_os(dcmweb_endpoint: str):
    """
    Delete metadata from OpenSearch using a query based on the DICOM web endpoint.

    :param dcmweb_endpoint: The endpoint of the external DICOM web service.
    """
    query = {
        "query": {
            "bool": {
                "must": {
                    "term": {
                        f"{HelperOpensearch.dcmweb_endpoint_tag}.keyword": dcmweb_endpoint
                    }
                }
            }
        }
    }
    logger.info(f"Deleting metadata from opensearch using query: {query}")
    HelperOpensearch.delete_by_query(query)


def start():
    """
    Main function to start the LocalExternalPacsOperator.

    :param operator_settings: The settings for the operator containing action and DAG run ID.
    :param kwargs: Additional keyword arguments from the Airflow context.
    """
    settings = OperatorSettings()
    operator_arguments = GetInputArguments()
    logger.debug(f"{settings=}")
    logger.debug(f"{operator_arguments=}")
    
    logger.info("# Starting module LocalExternalPacsOperator...")
    dag_run_id = operator_settings.dag_run_id

    workflow_form = kwargs["dag_run"].conf["workflow_form"]
    dcmweb_endpoint = workflow_form.get("dcmweb_endpoint")
    service_account_info = workflow_form.get("service_account_info")
    
    endpoint_manager = HelperDcmWebEndpointsManager(dag_run=kwargs["dag_run"])

    if operator_settings.action == "add" and dcmweb_endpoint and service_account_info:
        logger.info(f"Add to dcmweb minio list: {dcmweb_endpoint}")
        endpoint_manager.add_endpoint(dcmweb_endpoint=dcmweb_endpoint)
        logger.info(f"Adding secret: {dcmweb_endpoint}")
        service_account_info = decode_service_account_info(service_account_info)
        manage_secret(action="add", dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info)
        logger.info(f"Downloading metadata from {dcmweb_endpoint}")
        download_external_metadata(dcmweb_endpoint, workflow_form.get("ae_title", ""), service_account_info, kwargs["dag_run"].conf.get("output_dir"), dag_run_id)

    elif operator_settings.action == "delete":
        logger.info(f"Removing metadata: {dcmweb_endpoint}")
        delete_from_os(dcmweb_endpoint)
        logger.info(f"Removing secret: {dcmweb_endpoint}")
        manage_secret(action="delete", dcmweb_endpoint=dcmweb_endpoint)
        logger.info(f"Removing from dcmweb minio list: {dcmweb_endpoint}")
        endpoint_manager.remove_endpoint(dcmweb_endpoint=dcmweb_endpoint)

    else:
        logger.error(f"Unknown action: {operator_settings.action}")
        exit(1)


class LocalExternalPacsOperator(KaapanaPythonBaseOperator):
    """
    An operator for managing external PACS integrations, including downloading metadata and managing secrets.
    """
    def __init__(self, dag, **kwargs):
        """
        Initialize the LocalExternalPacsOperator.

        :param dag: The DAG object that this operator belongs to.
        :param kwargs: Additional keyword arguments for initialization.
        """
        action = kwargs.pop('action', "add")
        operator_settings = OperatorSettings(dag_run_id=kwargs["dag_run"].run_id, action=action)
        super().__init__(dag=dag, name="external_pacs_operator", batch_name=None, python_callable=start, operator_settings=operator_settings, **kwargs)
