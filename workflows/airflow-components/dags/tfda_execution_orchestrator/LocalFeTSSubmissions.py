import json
import os
import synapseclient as sc
import getpass
import requests

from subprocess import PIPE, run
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalFeTSSubmissions(KaapanaPythonBaseOperator):
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
                # json.load(fp_)

        open_list = []

        for s_id, s_state in subm_dict.items():
            if s_state == "open":
                open_list.append(s_id)
        
        print("Logging into Synapse...")
        syn = sc.login(email=synapse_user, apiKey=API_KEY)

        print("Logging into container registry!!!") 
        command = ["skopeo", "login", "--username", f"{synapse_user}", "--password", f"{synapse_pw}", f"{container_reg}"]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)

        print("\nChecking for new submissions...")
        for task_name, task_id in tasks:
            print(f"Checking {task_name}...")
            for subm in syn.getSubmissions(task_id):
                if subm["id"] not in subm_dict:

                    
                    print("Pulling container...")
                    command2 = ["skopeo", "copy", f"docker://{subm['dockerRepositoryName']}:latest", f"docker-archive:/root/airflow/dags/tfda_execution_orchestrator/tarball/{subm['id']}.tar", "--additional-tag", f"{subm['id']}:latest"]
                    output2 = run(command2, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
                    
                    print("Triggering isolated execution orchestrator...")
                    ## TODO iso env workflow with MedPerf eval client
                    self.conf = kwargs['dag_run'].conf
                    self.conf["subm_id"] = subm["id"]
                    self.trigger_dag_id = "tfda-execution-orchestrator"
                    # self.dag_run_id = kwargs['dag_run'].run_id
                    dag_run_id = generate_run_id(self.trigger_dag_id)
                    trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                                    replace_microseconds=False)
                    ## TODO add delay between sub-dag triggers

                    subm_dict[subm["id"]] = "open"
                    subm_dict[f'{subm["id"]}_registry'] = subm["dockerRepositoryName"]
                    open_list.append(subm["id"])
                    # time.sleep(60)

        print("Checking open tasks...")
        open_list_copy = open_list.copy()
        for s_id in open_list_copy:
            if os.path.exists(
                os.path.join(subm_logs_path, "fets_2022_test_queue", s_id, "end.txt")
            ):
                subm_dict[s_id] = "finished"
                open_list.remove(s_id)

        print("Saving submission dict...")
        with open(subm_dict_path, "w") as fp_:
            json.dump(subm_dict, fp_)

        print("\nTaking (coffee) a break now...")
        # time.sleep(60 * 60 * 1)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="evaluate-submissions",
            python_callable=self.start,
            **kwargs
        )