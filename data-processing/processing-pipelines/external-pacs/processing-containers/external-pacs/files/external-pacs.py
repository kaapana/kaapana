import base64
import json
import logging
import os
import traceback
from typing import Any, Dict, List

import requests
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch, DicomTags
from kaapanapy.helper import load_workflow_config, get_opensearch_client
from kaapanapy.settings import OperatorSettings

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class ExternalPacsOperator:
    """
    This operator is used to ADD external PACs to the project.
    It creates a kubernetes secret with credentials, adds the endpoint to the database, and download metadata of all instances.
    """
    
    DICOM_WEB_MULTIPLEXER_SERVICE = (
        "http://dicom-web-multiplexer-service.services.svc:8080/dicom-web-multiplexer"
    )

    def __init__(self):
        self.operator_settings = OperatorSettings()
        self.workflow_config = load_workflow_config()
        self.project_form: dict = self.workflow_config.get("project_form")
        self.workflow_form: dict = self.workflow_config.get("workflow_form")

    def start(self):
        """
        Starts the ExternalPacsOperator
        """
        logger.info("# Starting module ExternalPacsOperator...")

        dcmweb_endpoint = self.workflow_form.get("dcmweb_endpoint")
        service_account_info = self.workflow_form.get("service_account_info")

        if dcmweb_endpoint and service_account_info:
            service_account_info = self._decode_service_account_info(
                service_account_info
            )
            self.add_to_multiplexer(
                endpoint=dcmweb_endpoint, secret_data=service_account_info
            )

            self.download_external_metadata(
                dcmweb_endpoint,
                self.workflow_form.get("dataset_name", "external-data"),
            )

    def _filter_instances_to_import_by_series_uid(
        self, metadata: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filters DICOM instances by series UID to exclude those already imported locally.

        Parameters:
            metadata (List[Dict[str, Any]]): List of DICOM metadata dictionaries.

        Returns:
            List[Dict[str, Any]]: Filtered list of DICOM metadata.
        """

        def extract_series_uid(instance: Dict[str, Any]) -> str | None:
            return instance.get("0020000E", {"Value": [None]})["Value"][0]

        external_series_uids = list(set(map(extract_series_uid, metadata)))
        opensearch_index = self.project_form.get("opensearch_index")
        local_series_uids = set(
            map(
                lambda result: result["dcm-uid"]["series-uid"],
                HelperOpensearch().get_dcm_uid_objects(
                    series_instance_uids=external_series_uids, index=opensearch_index
                ),
            )
        )
        filtered_instances = list(
            filter(
                lambda instance: extract_series_uid(instance) not in local_series_uids,
                metadata,
            )
        )
        added_external_series_uid = list(set(map(extract_series_uid, metadata)))
        logger.info(
            f"{len(added_external_series_uid)} new series imported from {len(external_series_uids)}"
        )
        logger.info(
            f"{len(filtered_instances)} new instances imported from {len(metadata)}"
        )
        return filtered_instances

    def download_external_metadata(
        self,
        dcmweb_endpoint: str,
        dataset_name: str,
    ):
        """
        Downloads metadata from the specified DICOMweb endpoint, filtering and saving it locally.

        Parameters:
            dcmweb_endpoint (str): The DICOMweb endpoint from which to download metadata.
            dataset_name (str): Name of the dataset for identification.
        """
        dcmweb_helper = HelperDcmWeb()
        metadata = []

        studies = dcmweb_helper.get_studies(dcmweb_endpoint=dcmweb_endpoint)
        for study in studies:
            study_uid = study["0020000D"]["Value"][0]
            series = dcmweb_helper.get_series_of_study(
                study_uid, dcmweb_endpoint=dcmweb_endpoint
            )
            for single_series in series:
                series_uid = single_series["0020000E"]["Value"][0]
                instances = dcmweb_helper.get_instances_of_series(
                    study_uid=study_uid,
                    series_uid=series_uid,
                    dcmweb_endpoint=dcmweb_endpoint,
                )

                metadata.extend(instances)

        if not metadata:
            logger.error("No metadata found.")
            exit(1)

        logger.info(f"Found {len(metadata)} instances metadata")

        metadata = self._filter_instances_to_import_by_series_uid(metadata)
        for instance in metadata:
            self._save_instance_metadata(instance, dcmweb_endpoint, dataset_name)

    def _save_instance_metadata(
        self, instance: Dict[str, Any], dcmweb_endpoint: str, dataset_name: str
    ) -> None:
        """
        Saves metadata for a single DICOM instance to a JSON file.

        Parameters:
            instance (Dict[str, Any]): DICOM metadata dictionary for a single instance.
            dcmweb_endpoint (str): The DICOMweb endpoint from which metadata was downloaded.
            dataset_name (str): Name of the dataset for identification.
        """
        series_uid = instance.get("0020000E", {"Value": [None]})["Value"][0]
        if not series_uid:
            raise KeyError("Required field missing: Series UID (0020000E)")

        target_dir = os.path.join(
            self.operator_settings.workflow_dir,
            self.operator_settings.batch_name,
            series_uid,
            self.operator_settings.operator_out_dir,
        )
        os.makedirs(target_dir, exist_ok=True)
        json_path = os.path.join(target_dir, "metadata.json")

        instance["00020026"] = {"vr": "UR", "Value": [dcmweb_endpoint]}
        instance["00120010"] = {"vr": "LO", "Value": [dataset_name]}
        instance["00120020"] = {"vr": "LO", "Value": [self.project_form["name"]]}

        with open(json_path, "w", encoding="utf8") as fp:
            json.dump(instance, fp, indent=4, sort_keys=True)

    def delete_external_metadata(self, dcmweb_endpoint: str):
        """
        Deletes metadata from OpenSearch using a specified DICOMweb endpoint.

        Parameters:
            dcmweb_endpoint (str): The DICOMweb endpoint to query for deletion.
        """
        if dcmweb_endpoint:
            query = {
                "query": {
                    "bool": {
                        "must": {
                            "term": {
                                f"{DicomTags.dcmweb_endpoint_tag}.keyword": dcmweb_endpoint
                            }
                        }
                    }
                }
            }
            logger.info(f"Deleting metadata from opensearch using query: {query}")
            opensearch_index = self.project_form.get("opensearch_index")
            os_client = get_opensearch_client()
            os_client.delete_by_query(query, opensearch_index)

    def _decode_service_account_info(self, encoded_info: str) -> Dict[str, Any]:
        """
        Decodes a base64-encoded service account JSON string.

        Parameters:
            encoded_info (str): Base64-encoded service account JSON string.

        Returns:
            Dict[str, Any]: Decoded JSON dictionary.
        """
        decoded_bytes = base64.b64decode(encoded_info)
        decoded_string = decoded_bytes.decode("utf-8")
        return json.loads(decoded_string)

    def add_to_multiplexer(self, endpoint: str, secret_data: Dict[str, str]):
        """
        Adds an external PACS endpoint to the multiplexer with its secret data.
        Calls multiplexer service.

        Parameters:
            endpoint (str): The PACS endpoint to add.
            secret_data (Dict[str, str]): Dictionary containing secret data for the endpoint.

        Returns:
            bool: True if successfully added, False otherwise.
        """
        try:
            payload = {
                "dcmweb_endpoint": endpoint,
                "opensearch_index": self.project_form.get("opensearch_index"),
                "secret_data": secret_data,
            }
            response = requests.post(
                url=f"{self.DICOM_WEB_MULTIPLEXER_SERVICE}/datasources", json=payload
            )
            response.raise_for_status()
            logger.info(f"External PACs added to multiplexer successfully")

        except requests.exceptions.RequestException as e:
            logger.error(f"ERROR: External PACs couldn't be added to multiplexer: {e}")
            logger.error(traceback.format_exc())
            raise e


if __name__ == "__main__":
    operator = ExternalPacsOperator()
    operator.start()
