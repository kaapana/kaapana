import os
import logging
import subprocess
from subprocess import PIPE
from pathlib import Path
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

data_dir = getenv("DATADIR", "None")
data_dir = data_dir if data_dir.lower() != "none" else None
assert data_dir is not None

def start(self, ds, ti, **kwargs):
    print("Fetch the results...")
    workflow_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    base_dir = os.path.dirname(workflow_dir)
    results_path = os.path.join(base_dir, "minio", "results")
    Path(results_path).mkdir(parents=True, exist_ok=True)
    operator_dir = os.path.dirname(os.path.abspath(__file__))
    playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
    
    iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")

    conf = kwargs["dag_run"].conf
    platform_config = conf["platform_config"]
    
    workflow_type = conf["workflow_type"]
    user_experiment_name = conf["experiment_name"]
    platform_name = platform_config["default_platform"][workflow_type]
    flavor_name = platform_config["platforms"][platform_name]["default_flavor"][workflow_type]
    
    fetch_results_playbook_path = os.path.join(playbooks_dir, "fetch_results.yaml")
    if not os.path.isfile(fetch_results_playbook_path):
        raise AirflowFailException(f"Playbook '{fetch_results_playbook_path}' file not found!")
    
    ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["ssh_key_name"]
    remote_username = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["remote_username"]
    
    logging.info(f"Fetching results from isolated execution environment for {workflow_type} workflow...")
    playbook_args = f"target_host={iso_env_ip} ssh_key_name={ssh_key_name} remote_username={remote_username} results_path={results_path} user_experiment_name={user_experiment_name}"
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

start()