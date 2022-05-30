import os
import sys
import glob
import zipfile
from subprocess import PIPE, run
import re

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalCreateIsoInstanceOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        print("Starting an isolated environment...")

        operator_dir = os.path.dirname(os.path.abspath(__file__))
        scripts_dir = os.path.join(operator_dir, "scripts")
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        print(f'Playbooks directory is {playbooks_dir}, and scripts are in {scripts_dir}, and directory is {operator_dir}')
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
        playbooks_dir, "00_start_openstack_instance.yaml"
        )
        if not os.path.isfile(playbook_path):
            print("playbook yaml not found.")
            exit(1)
        
        os_project_name = "E230-TFDA"
        os_project_id = "f4a5b8b7adf3422d85b28b06f116941c"
        os_instance_name = "tfda-airflow-iso-envt"
        os_username = ""
        os_password = ""
        os_image = "a1f0cfe9-8761-41fc-bcbb-92cc1de034ae"
        # os_ssh_key = "kaapana"
        os_volume_size = "150"
        os_instance_flavor = "dkfz.gpu-V100S-16CD"

        extra_vars = f"os_project_name={os_project_name} os_project_id={os_project_id} os_username={os_username} os_password={os_password} os_instance_name={os_instance_name} os_image={os_image} os_volume_size={os_volume_size} os_instance_flavor={os_instance_flavor}"        
        command = ["ansible-playbook", playbook_path, "--extra-vars", extra_vars]
        output = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, timeout=6000)
        print(f'STD OUTPUT LOG is {output.stdout}')
        if output.returncode == 0:
            print(f'Iso Instance created successfully!')
            ## extract ip address from stdout
            # ip_addr_string = re.findall('isolated_env_ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output.stdout)
            ip_addr_string = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output.stdout)
            # ip_address = re.match('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', ip_addr_string)
            print(f'IP address of new TFDA isolated instance is: {ip_addr_string[-1]}')
            ti.xcom_push(key="iso_env_ip", value=ip_addr_string[-1])
        else:
            print(f"Failed to create isolated environment! ERROR LOGS:\n{output.stderr}")
        

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="create-iso-inst",
            python_callable=self.start,
            **kwargs
        )
