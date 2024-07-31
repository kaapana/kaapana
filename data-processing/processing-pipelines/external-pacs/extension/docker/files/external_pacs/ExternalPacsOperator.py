import base64
import json
import logging

from kaapana.kubetools.secret import (
    create_k8s_secret,
    delete_k8s_secret,
    get_k8s_secret,
    hash_secret_name,
)
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapana.operators.HelperOpensearch import HelperOpensearch
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class ExternalPacsOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        name: str = "external_pacs_operator",
        action: str = "add",
        **kwargs,
    ):
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)
        self.action = action

    def add_secret(self, service_account_info, dcmweb_endpoint):
        service_account_info["dcmweb_endpoint"] = dcmweb_endpoint

        helper = get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
        )
        if not helper.check_reachability():
            logger.error(f"Cannot reach {dcmweb_endpoint} with provided credentials.")
            logger.error("Not saving credentials and exiting!")
            exit(1)

        secret_name = hash_secret_name(dcmweb_endpoint=dcmweb_endpoint)
        create_k8s_secret(secret_name=secret_name, secret_data=service_account_info)

        secret = get_k8s_secret(secret_name=secret_name)
        if not secret:
            logger.error("Secret not created successfully")
            exit(1)
        else:
            logger.info("Secret successfully saved.")

    def delete_secret(self, dcmweb_endpoint):
        secret_name = hash_secret_name(dcmweb_endpoint=dcmweb_endpoint)
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

    def delete_from_os(self, dcmweb_endpoint):
        query = {
            "query": {
                "bool": {
                    "must": {
                        "match": {HelperOpensearch.dcmweb_endpoint_tag: dcmweb_endpoint}
                    }
                }
            }
        }
        HelperOpensearch.delete_by_query(query)

    @cache_operator_output
    def start(self, ds, **kwargs):
        workflow_form = kwargs["dag_run"].conf["workflow_form"]
        dcmweb_endpoint = workflow_form["dcmweb_endpoint"]

        if self.action == "add":
            logger.info(f"Add secret: {dcmweb_endpoint}")
            service_account_info = workflow_form["service_account_info"]
            decoded_bytes = base64.b64decode(workflow_form["service_account_info"])
            decoded_string = decoded_bytes.decode("utf-8")
            service_account_info = json.loads(decoded_string)

            logger.info(f"Service account info: {service_account_info}")
            self.add_secret(service_account_info, dcmweb_endpoint)
        elif self.action == "update":
            pass
        elif self.action == "delete":

            logger.info(f"Remove from OS: {dcmweb_endpoint}")
            self.delete_from_os(dcmweb_endpoint)
            logger.info(f"Remove secret: {dcmweb_endpoint}")
            self.delete_secret(dcmweb_endpoint)

        else:
            logger.error(f"Unknown action: {self.action}")
            exit(1)
