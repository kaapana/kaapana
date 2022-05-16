import os
import glob
import zipfile

from subprocess import PIPE, run
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalRunAlgoSendResultOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        print("Run algorithm in isolated environment and send result to source...")
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(operator_dir, "scripts")
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        subm_results_path = os.path.join(operator_dir, "subm_results")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and directory is {operator_dir}')
        
        playbook_path = os.path.join(
        playbooks_dir, "run_algo_send_result.yaml"
        )
        if not os.path.isfile(playbook_path):
            print("Playbook yaml file not found.")
            exit(1)
        
        subm_id = kwargs["dag_run"].conf["subm_id"]
        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")
        benchmark_id = "3"

        extra_vars = f"target_host={iso_env_ip} remote_username=ubuntu subm_id={subm_id} benchmark_id={benchmark_id} subm_results_path={subm_results_path}"
        command = ["ansible-playbook", playbook_path, "--extra-vars", extra_vars]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        print(f'STD OUTPUT LOG is {output.stdout}')
        if output.returncode == 0:
            print(f'Evaluation was successful and results were copied successfully! See full logs above...')
        else:
            print(f"Playbook FAILED! Cannot proceed further...\nERROR LOGS:\n{output.stderr}")
            exit(1)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="run-algo-send-results",
            python_callable=self.start,
            **kwargs
        )
