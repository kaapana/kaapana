import os
import glob
import zipfile
import logging
import subprocess
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalFetchResultsOperator(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        print("Fetch the results...")
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        results_path = os.path.join(operator_dir, "results")
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        
        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")

        platform_config = kwargs["dag_run"].conf["platform_config"]        
        request_config = kwargs["dag_run"].conf["request_config"]
        
        request_type = request_config["request_type"]
        platform_name = platform_config["default_platform"][request_type]
        flavor_name = platform_config["platforms"][platform_name]["default_flavor"][request_type]
        
        fetch_results_playbook_path = os.path.join(playbooks_dir, "fetch_results.yaml")
        if not os.path.isfile(fetch_results_playbook_path):
            raise AirflowFailException(f"Playbook '{fetch_results_playbook_path}' file not found!")
        
        # ssh_key_path = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["ssh_key_path"]
        ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["ssh_key_name"]
        remote_username = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["remote_username"]
        
        logging.info(f"Fetching results from isolated execution environment for {request_type} workflow...")
        playbook_args = f"target_host={iso_env_ip} ssh_key_name={ssh_key_name} remote_username={remote_username} results_path={results_path}"
        command = ["ansible-playbook", fetch_results_playbook_path, "--extra-vars", playbook_args]
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc == 0:
            logging.info(f"Results were fetched successfully!!")
        else:
            raise AirflowFailException("Fetching results FAILED! Cannot proceed further...")


    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="fetch-results",
            python_callable=self.start,
            **kwargs
        )
