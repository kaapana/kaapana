import os
import glob
import zipfile
from subprocess import PIPE, run

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalFeTSSubmissions(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        EMAIL = ""
        API_KEY = ""
        subm_logs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'subm_logs')

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
        syn = sc.login(email=EMAIL, apiKey=API_KEY)

        print("\nChecking for new submissions...")
            for task_name, task_id in tasks:
                print(f"Checking {task_name}...")

                task_dir = os.path.join(base_dir, task_name)
                for subm in syn.getSubmissions(task_id):
                    if subm["id"] not in subm_dict:
                        ## TODO MedPerf eval client, run here the sub-dag iso exec
                        # process_submission(subm, task_name, task_dir)
                        subm_dict[subm["id"]] = "open"
                        subm_dict[f'{subm["id"]}_registry'] = subm["dockerRepositoryName"]
                        open_list.append(subm["id"])
                        print("Logging into container registry!!!")
                        command = ["docker", "login", "docker.synapse.org", "-u", "kaushalap", "-p", "hubriFotuv@01"]
                        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
                        print("Pulling container...")
                        command2 = ["docker", "pull", subm["dockerRepositoryName"]]
                        output2 = run(command2, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
                        print("Saving container...")
                        command3 = ["docker", "save", subm["dockerRepositoryName"], "-o", f"{subm["id"]}.tar"]
                        output3 = run(command3, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)

                        # time.sleep(60)

            print("Checking open tasks...")
            open_list_copy = open_list.copy()
            for s_id in open_list_copy:
                if os.path.exists(os.path.join(subm_logs_path, "sample", s_id, "end.txt")) or os.path.exists(
                    os.path.join(subm_logs_path, "pixel", s_id, "end.txt")
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