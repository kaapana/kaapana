import base64
import json
import logging
import os
import traceback
from typing import Any, Dict

import requests
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapanapy.helper.HelperDcmWeb import HelperDcmWeb
from kaapanapy.helper.HelperOpensearch import HelperOpensearch

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class LocalExternalPacsOperator(KaapanaPythonBaseOperator):
    DICOM_WEB_MULTIPLEXER_SERVICE = (
        "http://dicom-web-multiplexer-service.services.svc:8080/dicom-web-multiplexer"
    )

    def __init__(
        self,
        dag,
        name: str = "external_pacs_operator",
        action: str = "add",
        **kwargs,
    ):
        super().__init__(
            dag=dag, name=name, batch_name=None, python_callable=self.start, **kwargs
        )
        self.action = action

    def _filter_instances_to_import_by_series_uid(self, metadata):
        def extract_series_uid(instance):
            return instance.get("0020000E", {"Value": [None]})["Value"][0]

        external_series_uids = list(set(map(extract_series_uid, metadata)))
        local_series_uids = set(
            map(
                lambda result: result["dcm-uid"]["series-uid"],
                HelperOpensearch.get_dcm_uid_objects(
                    series_instance_uids=external_series_uids
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
        logger.info(f"{len(added_external_series_uid)} new series imported from {len(external_series_uids)}")
        logger.info(
            f"{len(filtered_instances)} new instances imported from {len(metadata)}"
        )
        return filtered_instances

    def download_external_metadata(
        self,
        dcmweb_endpoint: str,
        dataset_name: str,
    ):
        # TODO get the DICOM_WEB_SERVICE from environment 
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

        logger.info(len(metadata))

        if not metadata or len(metadata) == 0:
            logger.error("No metadata found.")
            exit(1)

        logger.info(f"Found {len(metadata)} instances metadata")

        metadata = self._filter_instances_to_import_by_series_uid(metadata)
        for instance in metadata:
            series_uid = instance.get("0020000E", {"Value": [None]})["Value"][0]

            if not series_uid:
                raise KeyError(
                    f"Required field missing: Series UID (0020000E) in the series {instance}"
                )

            target_dir = os.path.join(
                self.airflow_workflow_dir,
                self.dag_run_id,
                "batch",
                series_uid,
                self.operator_out_dir,
            )

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            json_path = os.path.join(
                target_dir,
                "metadata.json",
            )
            # 00120010 ClinicalTrialSponsorName_keyword
            instance["00020026"] = {"vr": "UR", "Value": [dcmweb_endpoint]}
            instance["00120010"] = {"vr": "LO", "Value": [dataset_name]}

            project_name = self.project_form["name"]
            instance["00120020"] = {"vr": "LO", "Value": [project_name]}

            with open(json_path, "w", encoding="utf8") as fp:
                json.dump(instance, fp, indent=4, sort_keys=True)

    def delete_external_metadata(self, dcmweb_endpoint: str):
        if dcmweb_endpoint:
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

    def _decode_service_account_info(self, encoded_info: str) -> Dict[str, Any]:
        decoded_bytes = base64.b64decode(encoded_info)
        decoded_string = decoded_bytes.decode("utf-8")
        return json.loads(decoded_string)

    def add_to_multiplexer(self, endpoint: str, secret_data: Dict[str, str]):
        try:
            payload = {"endpoint": endpoint, "secret_data": secret_data}

            response = requests.post(
                url=f"{self.DICOM_WEB_MULTIPLEXER_SERVICE}/endpoints", json=payload
            )
            response.raise_for_status()
            logger.info(f"External PACs added to multiplexer successfully")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"ERROR: External PACs couldn't be added to multiplexer: {e}")
            logger.error(traceback.format_exc())
            return False

    def remove_from_multiplexer(self, endpoint: str):
        try:
            payload = {"endpoint": endpoint}
            response = requests.delete(
                f"{self.DICOM_WEB_MULTIPLEXER_SERVICE}/endpoints",
                json=payload,
            )
            response.raise_for_status()
            logger.info(f"External PACs {endpoint} successfully removed")
            return True
        
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating secret: {e}")
            logger.error(traceback.format_exc())
            return False

    @cache_operator_output
    def start(self, ds, **kwargs):
        logger.info("# Starting module LocalExternalPacsOperator...")
        # TODO Use kaapanapy.settings
        
        self.dag_run_id = kwargs["dag_run"].run_id
        self.workflow_config = kwargs["dag_run"].conf
        self.workflow_form = self.workflow_config["workflow_form"]
        self.project_form = self.workflow_config["project_form"]
        dcmweb_endpoint = self.workflow_form.get("dcmweb_endpoint")
        service_account_info = self.workflow_form.get("service_account_info")

        if self.action == "add" and dcmweb_endpoint and service_account_info:
            service_account_info = self._decode_service_account_info(
                service_account_info
            )
            if not self.add_to_multiplexer(
                endpoint=dcmweb_endpoint, secret_data=service_account_info
            ):
                exit(1)

            self.download_external_metadata(
                dcmweb_endpoint,
                self.workflow_form.get("dataset_name", "external-data"),
            )

        elif self.action == "delete":
            logger.info(f"Remove metadata: {dcmweb_endpoint}")
            self.delete_external_metadata(dcmweb_endpoint)
            if not self.remove_from_multiplexer(endpoint=dcmweb_endpoint):
                exit(1)

        else:
            logger.error(f"Unknown action: {self.action}")
            exit(1)
            logger.error(f"Unknown action: {self.action}")
            exit(1)
