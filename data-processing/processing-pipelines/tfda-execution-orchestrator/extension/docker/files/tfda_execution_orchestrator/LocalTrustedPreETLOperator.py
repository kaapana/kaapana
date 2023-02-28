import os
import logging
import requests
import subprocess
from subprocess import PIPE
from pathlib import Path
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalTrustedPreETLOperator(KaapanaPythonBaseOperator):
    def run_command(self, command):
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        return_code = process.poll()
        return return_code

    def algo_pre_etl(self, config_params):
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        user_experiment_path = os.path.join(operator_dir, "algorithm_files", config_params["workflow_type"], config_params["experiment_name"])
        Path(user_experiment_path).mkdir(parents=True, exist_ok=True)
        if config_params["workflow_type"] == "shell_workflow": 
            logging.debug("Downloading archive from provided URL for shell-workflow...")           
            download_url = config_params["download_url"]
            try:
                response = requests.get(download_url)
                response.raise_for_status()
                with open(os.path.join(user_experiment_path, f"{config_params['experiment_name']}.zip"), "wb") as file:
                    file.write(response.content)
            except requests.exceptions.RequestException as e:
                print(f"An error occurred while downloading the file: {e}")
        elif config_params["workflow_type"] == "container_workflow":
            logging.debug("Downloading container from registry since container workflow is requested...")
            container_registry_url = config_params['container_registry_url']
            container_registry_user = config_params['container_registry_user']
            container_registry_pwd = config_params['container_registry_pwd']
            container_name_version = config_params['container_name_version']
            logging.info("Logging into container registry...")
            command = ["skopeo", "login", "--username", f"{container_registry_user}", "--password", f"{container_registry_pwd}", f"{container_registry_url}"]
            return_code = self.run_command(command=command)
            if return_code == 0:
                logging.info(f"Login to the registry successful!!")
            else:
                raise AirflowFailException("Login to the registry FAILED! Cannot proceed further...")

            logging.debug(f"Pulling container: {container_name_version}...")
            tarball_file = os.path.join(user_experiment_path, f"{config_params['experiment_name']}.tar")
            if os.path.exists(tarball_file):
                logging.debug(f"Submission tarball already exists locally... deleting it now to pull latest!!")
                os.remove(tarball_file)
            """Due to absence of /etc/containers/policy.json in Airflow container, following Skopeo command only works with "--insecure-policy" """
            command2 = ["skopeo", "--insecure-policy", "copy", f"docker://{container_registry_url}/{container_name_version}", f"docker-archive:{tarball_file}", "--additional-tag", f"{container_name_version}"]
            return_code2 = self.run_command(command=command2)
            if return_code2 != 0:
                raise AirflowFailException(f"Error while trying to download container! Exiting...")        
        else:
            raise AirflowFailException(f"Workflow type {config_params['request_type']} not supported yet! Exiting...")

    
    def start(self, ds, ti, **kwargs):
        logging.info("Prepare data and algorithm before being loaded into the isolated environment...")
        conf = kwargs["dag_run"].conf
        """Prepare algorithm files"""
        self.algo_pre_etl(conf)


    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="trusted-pre-etl",
            python_callable=self.start,
            **kwargs
        )