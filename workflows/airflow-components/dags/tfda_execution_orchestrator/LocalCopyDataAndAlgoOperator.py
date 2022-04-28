import os
import glob
import zipfile

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalCopyDataAndAlgoOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Copy data and algorithm to isolated environment...")
        print(kwargs)
        dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(dir, "scripts")
        playbooks_dir = os.path.join(dir, "ansible_playbooks")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and directory is {dir}')
        
        platform_install_playbook_path = os.path.join(
        playbooks_dir, "copy_data_algo_to_iso_env.yaml"
        )
        if not os.path.isfile(platform_install_playbook_path):
            print("Playbook yaml file not found.")
            exit(1)

        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")
        algo_path = f"airflow/dags/tfda_execution_orchestrator/tarball/{tarball_file}"

        extra_vars = f"target_host={iso_env_ip} remote_username=root local_script=true install_script_path={install_script_path} registry_user={registry_user} registry_pwd={registry_pwd} registry_url={registry_url}"
        command = ["ansible-playbook", platform_install_playbook_path, "--extra-vars", extra_vars]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        print(f'STD OUTPUT LOG is {output.stdout}')
        if output.returncode == 0:
            print(f'Files copied successfully! See full logs above...')
        else:
            print(f"Playbook FAILED! Cannot proceed further...\nERROR LOGS:\n{output.stderr}")
            exit(1)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="copy-data-algo",
            python_callable=self.start,
            **kwargs
        )
