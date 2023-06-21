import os
import logging
import shutil
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR
from datetime import timedelta
from pathlib import Path


class LocalLoadPlatformConfigOperator(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        logging.info("Load platform specific configuration for the DAG run...")
        dag_run_id = kwargs["run_id"]
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        platform_config_path = os.path.join(
            operator_dir, "platform_specific_config", self.platform_config_file
        )
        dag_run_dir = os.path.join(AIRFLOW_WORKFLOW_DIR, dag_run_id)
        Path(dag_run_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(platform_config_path, dag_run_dir)

    def __init__(self, dag, platform_config_file="platform_config.json", **kwargs):
        super().__init__(
            dag=dag,
            name="load-platform-config",
            python_callable=self.start,
            execution_timeout=timedelta(hours=10),
            **kwargs
        )
        self.platform_config_file = platform_config_file
