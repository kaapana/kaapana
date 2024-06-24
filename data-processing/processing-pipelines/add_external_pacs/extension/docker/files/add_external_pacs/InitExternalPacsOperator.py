import json
import logging

from kaapana.kubetools.secret import create_k8s_secret, get_k8s_secret
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
        workflow_form = kwargs["dag_run"]["conf"]["workflow_form"]
        dcmweb_endpoint = workflow_form["dcmweb_endpoint"]
        service_account_info = json.loads(workflow_form["service_account_info"])

        helper = DcmWeb.get_dcmweb_helper(
            dcmweb_endpoint=dcmweb_endpoint, service_account_info=service_account_info
        )
        if not helper.check_reachability():
            logger.error(f"Cannot reach {dcmweb_endpoint} with provided credentials.")
            logger.error("Not saving credentials and exiting!")
            exit(1)

        create_k8s_secret(
            secret_name="", namespace="services", credentials=service_account_info
        )

        secret = get_k8s_secret(secret_name=dcmweb_endpoint, namespace="services")
        if not secret:
            logger.error("Secret not created sucessfully")
            exit(1)
        else:
            logger.info("Secret sucessfully saved.")
