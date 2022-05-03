import os
import glob
import zipfile
from subprocess import PIPE, run

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalDeleteIsoEnvOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        print("Delete isolated environment...")

        operator_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(operator_dir, "scripts")
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and directory is {operator_dir}')

        playbook_path = os.path.join(
        playbooks_dir, "05_delete_os_instance.yaml"
        )
        if not os.path.isfile(playbook_path):
            print("playbook yaml not found.")
            exit(1)
        
        os_project_name = "E230-TFDA"
        os_project_id = "f4a5b8b7adf3422d85b28b06f116941c"
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
