import base64
import json
import logging
import os
from typing import Any, Dict

from external_pacs.HelperDcmWebEndpointsManager import HelperDcmWebEndpointsManager
from external_pacs.utils import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class LocalExternalPacsOperator(KaapanaPythonBaseOperator):

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

    def _decode_service_account_info(self, encoded_info: str) -> Dict[str, Any]:
        decoded_bytes = base64.b64decode(encoded_info)
        decoded_string = decoded_bytes.decode("utf-8")
        return json.loads(decoded_string)

    def _filter_series_to_import(self, metadata):
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
        filtered_series = list(
            filter(
                lambda instance: extract_series_uid(instance) not in local_series_uids,
                metadata,
            )
        )
        logger.info(
            f"{len(filtered_series)} new series imported from {len(external_series_uids)}"
        )
        return filtered_series

    def download_external_metadata(
        self, dcmweb_endpoint: str, dataset_name: str, service_account_info: Dict[str, Any]
    ):
        logger.info(f"Adding external metadata: {dcmweb_endpoint}")
        dcmweb_helper = get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
        )
        metadata = dcmweb_helper.search_for_instances()

        if not metadata or len(metadata) == 0:
            logger.error("No metadata found.")
            exit(1)
        logger.info(f"Found {len(metadata)} series")

        metadata = self._filter_series_to_import(metadata)
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

    def add_secret(self, dcmweb_endpoint: str, service_account_info: Dict[str, str]):
        helper = get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
        )
        if not helper:
            logger.error(
                f"Cannot create HelperDcmWeb {dcmweb_endpoint} with provided credentials."
            )
            logger.error("Not saving credentials and exiting!")
            exit(1)

        if not helper.check_reachability():
            logger.error(f"Cannot reach {dcmweb_endpoint} with provided credentials.")
            logger.error("Not saving credentials and exiting!")
            exit(1)

        secret_name = hash_secret_name(name=dcmweb_endpoint)
        create_k8s_secret(secret_name=secret_name, secret_data=service_account_info)

        secret = get_k8s_secret(secret_name=secret_name)
        if not secret:
            logger.error("Secret not created successfully")
            exit(1)
        else:
            logger.info("Secret successfully saved.")

    def delete_secret(self, dcmweb_endpoint: str):
        secret_name = hash_secret_name(name=dcmweb_endpoint)
        secret = get_k8s_secret(secret_name=secret_name)
        if not secret:
            logger.error("No secret to remove, can't remove.")
            exit(1)

        delete_k8s_secret(secret_name)
        secret = get_k8s_secret(secret_name=secret_name)
        if not secret:
            logger.info("Secret successfully removed.")
        else:
            logger.error("Secret not created successfully")
            exit(1)

    def delete_from_os(self, dcmweb_endpoint: str):
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

    
    @cache_operator_output
    def start(self, ds, **kwargs):
        logger.info("# Starting module LocalExternalPacsOperator...")
        self.dag_run_id = kwargs["dag_run"].run_id
        self.workflow_config = kwargs["dag_run"].conf
        self.workflow_form = self.workflow_config["workflow_form"]
        self.project_form = self.workflow_config["project_form"]
        dcmweb_endpoint = self.workflow_form.get("dcmweb_endpoint")
        service_account_info = self.workflow_form.get("service_account_info")

        endpoint_manager = HelperDcmWebEndpointsManager(dag_run=kwargs["dag_run"])

        if self.action == "add" and dcmweb_endpoint and service_account_info:
            logger.info(f"Add to dcmweb minio list: {dcmweb_endpoint}")
            endpoint_manager.add_endpoint(dcmweb_endpoint=dcmweb_endpoint)
            logger.info(f"Add secret: {dcmweb_endpoint}")
            service_account_info = self._decode_service_account_info(
                service_account_info
            )
            self.add_secret(dcmweb_endpoint, service_account_info)
            logger.info(f"Downloading metadata from {dcmweb_endpoint}")
            self.download_external_metadata(
                dcmweb_endpoint, self.workflow_form.get("dataset_name", ""), service_account_info
            )

        elif self.action == "delete":
            logger.info(f"Remove metadata: {dcmweb_endpoint}")
            self.delete_from_os(dcmweb_endpoint)
            logger.info(f"Remove secret: {dcmweb_endpoint}")
            self.delete_secret(dcmweb_endpoint)
            logger.info(f"Remove from dcmweb minio list: {dcmweb_endpoint}")
            endpoint_manager.remove_endpoint(dcmweb_endpoint=dcmweb_endpoint)

        else:
            logger.error(f"Unknown action: {self.action}")
            exit(1)
