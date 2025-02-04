import base64
import json
import logging
import os
from typing import Any, Dict, List

import requests
from CustomHelperDcmWeb import CustomHelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch, DicomTags
from kaapanapy.helper import load_workflow_config, get_opensearch_client
from kaapanapy.settings import OperatorSettings
from kaapanapy.logger import get_logger


logger = get_logger(__file__)


class ExternalPacsOperator:
    """
    Operator to manage external PACS connections within the project.

    This operator allows the addition and removal of external PACS by interacting with
    DICOMweb endpoints, updating the project's metadata database, and managing Kubernetes secrets.
    """

    def __init__(self):
        """
        Initializes the `ExternalPacsOperator` instance.

        Attributes:
            operator_settings (OperatorSettings): Settings for the operator.
            workflow_config (dict): Configuration data for the workflow.
            project_form (dict): Project-specific configuration.
            workflow_form (dict): Workflow-specific configuration.
            dcmweb_helper (CustomHelperDcmWeb): Helper instance for interacting with DICOMweb endpoints.
            action (str): The operation to perform ("add" or "remove").
        """
        self.operator_settings = OperatorSettings()
        self.workflow_config = load_workflow_config()
        self.project_form: dict = self.workflow_config.get("project_form")
        self.workflow_form: dict = self.workflow_config.get("workflow_form")
        self.dcmweb_helper = CustomHelperDcmWeb()
        logger.info(self.dcmweb_helper.dcmweb_rs_endpoint)
        logger.info(self.dcmweb_helper.dcmweb_uri_endpoint)
        self.action = os.getenv("ACTION")
        if not self.action or self.action not in ["add", "remove"]:
            logger.error("No action")
            exit(1)

    def start(self):
        """
        Starts the `ExternalPacsOperator`.

        This method executes the appropriate action (`add` or `remove`) based on the configured action.
        """
        logger.info("# Starting module ExternalPacsOperator...")

        dcmweb_endpoint = self.workflow_form.get("dcmweb_endpoint", "").strip()
        assert dcmweb_endpoint, "DcmWeb endpoint argument missing. Abort!"

        if self.action == "add":
            service_account_info = self.workflow_form.get("service_account_info")
            assert (
                service_account_info
            ), "Service Account Information (credentials) missing. Abort!"

            service_account_info = self._decode_service_account_info(
                service_account_info
            )

            self.add_to_multiplexer(dcmweb_endpoint, service_account_info)

            self.download_external_metadata(
                dcmweb_endpoint,
                self.workflow_form.get("dataset_name", "external-data"),
            )

        elif self.action == "remove":
            self.remove_from_multiplexer(dcmweb_endpoint)
            self.remove_external_metadata(dcmweb_endpoint)

        else:
            logger.info("Unknown action: {self.action}")
            exit(1)

    def _filter_instances_to_import_by_series_uid(
        self, metadata: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Filters DICOM instances by Series UID to exclude those already imported locally.

        Args:
            metadata (List[Dict[str, Any]]): List of DICOM metadata dictionaries.

        Returns:
            List[Dict[str, Any]]: Filtered list of DICOM instances.
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
        added_external_series_uid = list(
            set(map(extract_series_uid, filtered_instances))
        )

        logger.info(
            f"External PACS: {len(external_series_uids)} series available\n"
            f"OpenSearch (local & remote): {len(added_external_series_uid) - len(added_external_series_uid)} series found\n"
            f"Importing: {len(added_external_series_uid)} new series\n"
        )

        logger.info(
            f"External PACS: {len(metadata)} instances available\n"
            f"OpenSearch (local & remote): {len(added_external_series_uid) - len(added_external_series_uid)} instances found\n"
            f"Importing: {len(filtered_instances)} new instances\n"
        )
        return filtered_instances

    def download_external_metadata(
        self,
        dcmweb_endpoint: str,
        dataset_name: str,
    ):
        """
        Downloads metadata from an external DICOMweb endpoint.

        Args:
            dcmweb_endpoint (str): URL of the DICOMweb endpoint to download metadata from.
            dataset_name (str): Name of the dataset being imported.
        """
        metadata = []

        studies = self.dcmweb_helper.get_studies(dcmweb_endpoint=dcmweb_endpoint)
        for study in studies:
            study_uid = study["0020000D"]["Value"][0]
            series = self.dcmweb_helper.get_series_of_study(
                study_uid, dcmweb_endpoint=dcmweb_endpoint
            )
            for single_series in series:
                series_uid = single_series["0020000E"]["Value"][0]
                instances = self.dcmweb_helper.get_instances_of_series(
                    study_uid=study_uid,
                    series_uid=series_uid,
                    dcmweb_endpoint=dcmweb_endpoint,
                )
                for instance in instances:
                    instance_dict = dict(instance)
                    instance_dict["0020000D"]["Value"] = [study_uid]
                    instance_dict["0020000E"]["Value"] = [series_uid]
                    metadata.append(instance_dict)

        if not metadata:
            logger.error("No metadata found.")
            exit(1)

        logger.info(f"Found {len(metadata)} instances metadata")
        metadata = self._filter_instances_to_import_by_series_uid(metadata)
        success = 0
        total = len(metadata)
        for instance in metadata:
            study_uid = instance["0020000D"]["Value"][0]
            series_uid = instance["0020000E"]["Value"][0]
            instance_uid = instance["00080018"]["Value"][0]

            full_instance_metadata = self.dcmweb_helper.get_instance_metadata(
                study_uid=study_uid,
                series_uid=series_uid,
                instance_uid=instance_uid,
                dcmweb_endpoint=dcmweb_endpoint,
            )
            if len(metadata) > 1:
                self._save_instance_metadata(
                    full_instance_metadata[0], dcmweb_endpoint, dataset_name
                )
                success += 1
            else:
                logger.error("Metadata empty")

        logger.info(f"Saved instances:[{success}/{total}]")

    def _save_instance_metadata(
        self, instance: Dict[str, Any], dcmweb_endpoint: str, dataset_name: str
    ) -> None:
        """
        Saves metadata of a single DICOM instance to a local JSON file.

        Args:
            instance (Dict[str, Any]): Metadata dictionary of the DICOM instance.
            dcmweb_endpoint (str): DICOMweb endpoint URL.
            dataset_name (str): Name of the dataset being imported.
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

        instance["00020016"] = {
            "vr": "UR",
            "Value": [self.extract_datasource_name(dcmweb_endpoint)],
        }
        instance["00020026"] = {"vr": "UR", "Value": [dcmweb_endpoint]}
        instance["00120010"] = {"vr": "LO", "Value": [dataset_name]}
        instance["00120020"] = {"vr": "LO", "Value": [self.project_form["name"]]}

        with open(json_path, "w", encoding="utf8") as fp:
            json.dump(instance, fp, indent=4, sort_keys=True)

    def extract_datasource_name(self, dcmweb_endpoint: str):
        """
        Extracts the data source name based on the DICOMweb endpoint.

        Args:
            dcmweb_endpoint (str): DICOMweb endpoint URL.

        Returns:
            str: Name of the data source (e.g., "gcloud", "dcm4chee", "orthanc").
        """
        if "google" in dcmweb_endpoint:
            return "gcloud"
        elif "dcm4chee" in dcmweb_endpoint:
            return "dcm4chee"
        elif "orthanc" in dcmweb_endpoint:
            return "orthanc"

    def remove_external_metadata(self, dcmweb_endpoint: str):
        """
        Removes metadata associated with a specified DICOMweb endpoint from OpenSearch.

        Args:
            dcmweb_endpoint (str): DICOMweb endpoint URL.
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
            os_client.delete_by_query(opensearch_index, query)

    def _decode_service_account_info(self, encoded_info: str) -> Dict[str, Any]:
        """
        Decodes base64-encoded service account information.

        Args:
            encoded_info (str): Base64-encoded JSON string containing service account details.

        Returns:
            Dict[str, Any]: Decoded service account information.
        """
        decoded_bytes = base64.b64decode(encoded_info)
        decoded_string = decoded_bytes.decode("utf-8")
        return json.loads(decoded_string)

    def add_to_multiplexer(self, dcmweb_endpoint: str, secret_data: Dict[str, str]):
        """
        Adds an external PACS to the multiplexer.

        Args:
            dcmweb_endpoint (str): DICOMweb endpoint URL.
            secret_data (Dict[str, str]): Dictionary containing credentials for accessing the PACS.
        """
        payload = {
            "datasource": {
                "dcmweb_endpoint": dcmweb_endpoint,
                "project_index": self.project_form.get("opensearch_index"),
            },
            "secret_data": secret_data,
        }
        logger.info(f"Payload being sent: {payload}")
        response = requests.post(
            url=f"{self.dcmweb_helper.dcmweb_rs_endpoint}/management/datasources",
            json=payload,
        )
        response.raise_for_status()
        logger.info(f"External PACs added to multiplexer successfully")

    def remove_from_multiplexer(self, dcmweb_endpoint: str):
        """
        Removes an external PACS from the multiplexer.

        Args:
            dcmweb_endpoint (str): DICOMweb endpoint URL.
        """
        payload = {
            "dcmweb_endpoint": dcmweb_endpoint,
            "project_index": self.project_form.get("opensearch_index"),
        }
        logger.info(f"Payload being sent: {payload}")
        response = requests.delete(
            url=f"{self.dcmweb_helper.dcmweb_rs_endpoint}/management/datasources",
            json=payload,
        )
        response.raise_for_status()
        logger.info(f"External PACs remove from multiplexer successfully")


if __name__ == "__main__":
    operator = ExternalPacsOperator()
    operator.start()
