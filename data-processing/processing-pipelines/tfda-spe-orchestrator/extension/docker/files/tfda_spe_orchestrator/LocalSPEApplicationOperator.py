import logging
import os
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR


## TODO This operator still needs to be tested
class LocalSPEApplicationOperator(KaapanaApplicationOperator):
    """
    This class is a custom operator that extends the functionality of the KaapanaApplicationOperator.
    The operator loads the IP address of an SPE VM from a file and includes it in the application payload before calling the parent class's start method.
    """

    def start(self, ds, ti, **kwargs):
        logging.info(
            "Loading the IP address of SPE and passing it to application payload..."
        )
        iso_env_ip_path = os.path.join(
            AIRFLOW_WORKFLOW_DIR, kwargs["run_id"], "iso_env_ip.txt"
        )
        with open(iso_env_ip_path, "r") as file:
            iso_env_ip = file.read().rstrip()
        self.payload["sets"]["global.VNC_SERVER"] = f"{iso_env_ip}:5901"
        logging.info("Loading completed successfully!")

    def __init__(self, dag, **kwargs):
        super().__init__(dag=dag, python_callable=self.start, **kwargs)
