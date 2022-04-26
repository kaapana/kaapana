import os
import glob
import zipfile
from subprocess import PIPE, run

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalInstallPlatformDepsOnIsoEnvOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        print("Installing platform dependencies on isolated environment...")
        print(kwargs)

        dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(dir, "scripts")
        playbooks_dir = os.path.join(dir, "ansible_playbooks")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and directory is {dir}')
        # run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        # batch_input_dir = os.path.join(run_dir, self.operator_in_dir)
        # print('input_dir', batch_input_dir)

        # batch_output_dir = os.path.join(run_dir, self.operator_out_dir)  # , project_name)
        # if not os.path.exists(batch_output_dir):
        #     os.makedirs(batch_output_dir)

        # for file_path in glob.glob(os.path.join(batch_input_dir, '*.zip')):
        #     with zipfile.ZipFile(file_path, 'r') as zip_ref:
        #         zip_ref.extractall(batch_output_dir)

        server_deps_playbook_path = os.path.join(
        playbooks_dir, "01_install_server_dependencies.yaml"
        )
        if not os.path.isfile(server_deps_playbook_path):
            print("Server dependencies installer playbook yaml file not found.")
            exit(1)

        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")
        install_script_path = "airflow/dags/tfda_execution_orchestrator/install_scripts"
        extra_vars = f"target_host={iso_env_ip} remote_username=root local_script=true install_script_path={install_script_path}"
        command = ["ansible-playbook", server_deps_playbook_path, "--extra-vars", extra_vars]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        print(f'STD OUTPUT LOG is {output.stdout}')
        if output.returncode == 0:
            print(f'Platform dependencies installed successfully! See full logs above...')
        else:
            print(f"Platform dependencies couldn't be installed successfully! Cannot proceed further...\nERROR LOGS:\n{output.stderr}")
            exit(1)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="install-platform-dependencies",
            python_callable=self.start,
            **kwargs
        )
