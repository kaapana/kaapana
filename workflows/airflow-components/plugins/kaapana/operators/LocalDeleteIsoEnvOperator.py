import os
import glob
import zipfile
from subprocess import PIPE, run

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteIsoEnvOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Delete isolated environment...")
        print(kwargs)

        kaapana_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scripts_dir = os.path.join(kaapana_dir, "CI", "scripts")
        playbooks_dir = os.path.join(kaapana_dir, "CI", "ansible_playbooks")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and kaapana dir is {kaapana_dir}')
        # run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        # batch_input_dir = os.path.join(run_dir, self.operator_in_dir)
        # print('input_dir', batch_input_dir)

        # batch_output_dir = os.path.join(run_dir, self.operator_out_dir)  # , project_name)
        # if not os.path.exists(batch_output_dir):
        #     os.makedirs(batch_output_dir)

        # for file_path in glob.glob(os.path.join(batch_input_dir, '*.zip')):
        #     with zipfile.ZipFile(file_path, 'r') as zip_ref:
        #         zip_ref.extractall(batch_output_dir)

        playbook_path = os.path.join(
        playbooks_dir, "05_delete_os_instance.yaml"
        )
        if not os.path.isfile(playbook_path):
            print("playbook yaml not found.")
            exit(1)
        
        os_project_name = "E230-Kaapana-CI"
        os_project_id = "2df9e30325c849dbadcc07d7ffd4b0d6"
        os_instance_name = "tfda-airfl-iso-env-test"
        os_username = ""
        os_password = ""
        extra_vars = f"os_project_name={os_project_name} os_project_id={os_project_id} os_username={os_username} os_password={os_password} os_instance_name={os_instance_name}"
        command = ["ansible-playbook", playbook_path, "--extra-vars", extra_vars]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        print(f'STD OUTPUT LOG is {output.stdout}')
        if output.returncode == 0:
            print(f'Instance deleted successfully! See full logs above...')
        else:
            print(f"FAILED to delete instance! See ERROR LOGS:\n{output.stderr}")
            exit(1)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="delete-iso-env",
            python_callable=self.start,
            **kwargs
        )
