import os
import logging
import subprocess
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalRunAlgoOperator(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        print("Run algorithm in isolated environment...")
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        
        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")
        conf = kwargs["dag_run"].conf
        platform_config = conf["platform_config"]
        
        workflow_type = conf["workflow_type"]
        platform_name = platform_config["default_platform"][workflow_type]
        flavor_name = platform_config["platforms"][platform_name]["default_flavor"][workflow_type]
        
        run_workflow_playbook_path = os.path.join(playbooks_dir, f"run_{workflow_type}.yaml")
        if not os.path.isfile(run_workflow_playbook_path):
            raise AirflowFailException(f"Playbook '{run_workflow_playbook_path}' file not found!")
        
        user_selected_data = conf["bucket_id"]
        user_experiment_name = conf["experiment_name"]
        user_container_name_version = conf["container_name_version"]
        
        # ssh_key_path = platform_config["platform_config"][platform_name]["platform_flavors"][flavor_name]["ssh_key_path"]
        ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["ssh_key_name"]
        remote_username = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["remote_username"]

        logging.info(f"Running {workflow_type}...")
        playbook_args = f"target_host={iso_env_ip} ssh_key_name={ssh_key_name} user_experiment_name={user_experiment_name} user_selected_data={user_selected_data} user_container_name_version={user_container_name_version} remote_username={remote_username}"
        command = ["ansible-playbook", run_workflow_playbook_path, "--extra-vars", playbook_args]
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc == 0:
            logging.info(f"Algorithm ran successfully!!")
        else:
            raise AirflowFailException("Running workflow FAILED! Cannot proceed further...")


    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="run-isolated-workflow",
            python_callable=self.start,
            **kwargs
        )
