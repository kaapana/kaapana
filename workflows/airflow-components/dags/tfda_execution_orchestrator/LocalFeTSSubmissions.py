import json
import os
import synapseclient as sc
import getpass
import requests

from subprocess import PIPE, run
from airflow.models import DagRun
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalFeTSSubmissions(KaapanaPythonBaseOperator):
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        synapse_user = ""
        API_KEY = ""
        synapse_pw = ""
        container_reg = "docker.synapse.org"
        base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        subm_logs_path = os.path.join(base_dir, "subm_logs")
        tasks = [("fets_2022_test_queue", 9615030)]

        subm_dict = {}
        subm_dict_path = os.path.join(subm_logs_path, "subm_dict.json")

        if os.path.exists(subm_dict_path):
            with open(subm_dict_path, "r") as fp_:
                subm_dict = json.load(fp_)
        
        print("Logging into Synapse...")
        syn = sc.login(email=synapse_user, apiKey=API_KEY)

        print("Logging into container registry!!!") 
        command = ["skopeo", "login", "--username", f"{synapse_user}", "--password", f"{synapse_pw}", f"{container_reg}"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        if output.returncode != 0:
            print(f"Error logging into container registry! Exiting... \nERROR LOGS: {output.stderr}")
            exit(1)

        print("Checking for new submissions...")
        for task_name, task_id in tasks:
            print(f"Checking {task_name}...")
            for subm in syn.getSubmissions(task_id):
                if subm["id"] not in subm_dict:                    
                    print("Pulling container...")
                    command2 = ["skopeo", "copy", f"docker://{subm['dockerRepositoryName']}:latest", f"docker-archive:/root/airflow/dags/tfda_execution_orchestrator/tarball/{subm['id']}.tar", "--additional-tag", f"{subm['id']}:latest"]
                    output2 = run(command2, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
                    if output2.returncode != 0:
                        print(f"Error while trying to download container! Skipping... ERROR LOGS:\n {output2.stderr} ")
                        subm_dict[subm["id"]] = "skipped"
                        continue
                    
                    print("Triggering isolated execution orchestrator...")
                    self.trigger_dag_id = "tfda-execution-orchestrator"
                    # self.dag_run_id = kwargs['dag_run'].run_id
                    self.conf = kwargs['dag_run'].conf
                    self.conf["subm_id"] = subm["id"]
                    dag_run_id = generate_run_id(self.trigger_dag_id)
                    try:
                        trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                                        replace_microseconds=False)
                    except Exception as e:
                        print(f"Error while triggering isolated workflow for submission with ID: {subm['id']}...")
                        print(e)
                        subm_dict[subm["id"]] = "exception"

                    dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                    if dag_run:
                        print(f'The latest isolated workflow has been triggered at: {dag_run.execution_date}!!!')

                    dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)

                    while dag_state['state'] != "failed" and dag_state['state'] != "success":
                        dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
                        dag_state = get_dag_run_state(dag_id="tfda-execution-orchestrator", execution_date=dag_run.execution_date)                        
                    
                    if dag_state['state'] == "failed":
                        print(f"**************** The evaluation of submission with ID {subm['id']} has FAILED ****************")
                        subm_dict[subm['id']] = "failed"
                    if dag_state['state'] == "success":
                        print(f"**************** The evaluation of submission with ID {subm['id']} was SUCCESSFUL ****************")
                        subm_dict[subm['id']] = "success"

        print("Saving submission dict...")
        with open(subm_dict_path, "w") as fp_:
            json.dump(subm_dict, fp_)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="evaluate-submissions",
            python_callable=self.start,
            **kwargs
        )