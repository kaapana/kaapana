import os
import logging
import shutil
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR
from datetime import timedelta
from pathlib import Path


class LocalLoadPlatformConfigOperator(KaapanaPythonBaseOperator):
    """
    Custom operator for loading platform-specific configuration for a Secure Processing Environment (SPE).

    This operator extends the KaapanaPythonBaseOperator and is designed to handle the task of loading platform-specific
    configuration files for an SPE. It copies the specified platform configuration file from the operator's
    directory to the DAG run's directory so that it can be used further in the pipeline.

    Parameters:
        platform_config_file (str, optional): The name of the platform-specific configuration file to be loaded.
                                              This file should be present in the 'platform_specific_config'
                                              subdirectory relative to the directory where this operator is defined.
                                              The default value is 'platform_config.json'.

    Notes:
        1. The 'platform_config_file' should be a valid JSON file containing platform-specific configuration data.
        2. Ensure that the 'platform_specific_config' subdirectory exists relative to the directory where this operator
           is defined, and it contains the specified 'platform_config_file'.
    """

    def start(self, ds, ti, **kwargs):
        logging.info("Load platform specific configuration for the DAG run...")
        dag_run_id = kwargs["dag_run"].run_id
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        platform_config_path = os.path.join(
            operator_dir, "platform_specific_config", self.platform_config_file
        )
        dag_run_dir = os.path.join(AIRFLOW_WORKFLOW_DIR, dag_run_id)
        Path(dag_run_dir).mkdir(parents=True, exist_ok=True)
        shutil.copy(platform_config_path, dag_run_dir)

        ## Code for loading platform config as passed via the SPE Admin UI
        # logging.info("Load platform specific configuration for the DAG run...")
        # dag_run_id = kwargs["dag_run"].run_id
        # dag_conf = kwargs["dag_run"].conf
        # dag_run_config_dir = os.path.join(AIRFLOW_WORKFLOW_DIR, dag_run_id)
        # Path(dag_run_config_dir).mkdir(parents=True, exist_ok=True)
        # dag_run_config_path = os.path.join(dag_run_config_dir, self.platform_config_file)
        # with open(dag_run_config_path, "w") as fp:
        #     json.dump(dag_conf, fp, indent=2)

    def __init__(self, dag, platform_config_file="platform_config.json", **kwargs):
        super().__init__(
            dag=dag,
            name="load-platform-config",
            python_callable=self.start,
            execution_timeout=timedelta(hours=10),
            **kwargs
        )
        self.platform_config_file = platform_config_file
