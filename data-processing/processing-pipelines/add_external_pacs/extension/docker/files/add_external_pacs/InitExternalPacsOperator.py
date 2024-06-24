import json
import logging

from kaapana.operators.DcmWeb import DcmWeb
from kaapana.operators.HelperCaching import cache_operator_output
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__file__)


class InitExternalPacsOperator(KaapanaPythonBaseOperator):
    def __init__(
        self,
        dag,
        name: str = "init_external_pacs_operator",
        **kwargs,
    ):
        super().__init__(dag=dag, name=name, python_callable=self.start, **kwargs)

    @cache_operator_output
    def start(self, ds, **kwargs):
        # TODO GET WORKFLOW FORM DATA
        workflow_form = kwargs["dag_run"]["conf"]["workflow_form"]
        dcmweb_endpoint = workflow_form["dcmweb_endpoint"]
        service_account_info = json.loads(workflow_form["service_account_info"])

        # TODO CHECK REACHABILITY USING PROVIDED CREDENTIALS AND URL
        helper = DcmWeb.get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
        )
        if not helper.check_reachability():
            logger.error(f"Cannot reach {dcmweb_endpoint} with provided credentials.")
            exit(1)

        # TODO CREATE NAMESPACE SECRET AND DO A SANITY CHECK (TRY TO ACCESS IT)
        update_k8s_secret(
            secret_name=dcmweb_endpoint, namespace="admin", secret_data=credentials
        )
        secret = get_k8s_secret(secret_name=dcmweb_endpoint, namespace="admin")
