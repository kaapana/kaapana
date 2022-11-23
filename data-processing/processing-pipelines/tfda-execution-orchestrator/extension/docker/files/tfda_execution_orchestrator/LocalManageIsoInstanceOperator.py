import os
import glob
import zipfile
import subprocess
import re
import logging
from airflow.exceptions import AirflowFailException
from subprocess import PIPE
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalManageIsoInstanceOperator(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        if self.instanceState == "present":
            logging.info("Starting an isolated environment...")
        elif self.instanceState == "absent":
            logging.info("Deleting isolated environment...")

        request_config = kwargs["dag_run"].conf["request_config"]
        request_type = request_config["request_type"]

        platform_config = kwargs["dag_run"].conf["platform_config"]
        platform_name = platform_config["default_platform"][request_type]
        flavor_name = platform_config["platforms"][platform_name]["default_flavor"][request_type]
        
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        playbook_path = os.path.join(playbooks_dir, "manage_"+platform_name+"_instance.yaml")
        if not os.path.isfile(playbook_path):
            raise AirflowFailException(f"Playbook '{playbook_path}' file not found!")

        playbook_args = f"instance_name={request_type}_instance instance_state={self.instanceState}"
        
        if platform_name in ["openstack", "qemu_kvm"]:
            for key, value in platform_config["platforms"][platform_name]["platform_flavors"][flavor_name].items():
                playbook_args += f" {key}={value}"
        else:
            raise AirflowFailException(f"Sorry!! {platform_name.title()} is not yet supported. Please choose a supported platform...")
        
        # print(f"*****************************The EXTRA-VARS are: {playbook_args}************************************")
        if platform_name in "qemu_kvm":
            vault_text_file = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["vault_text_file"]
            vault_filepath = os.path.join(playbooks_dir, vault_text_file)
            if not os.path.isfile(vault_filepath):
                raise AirflowFailException(f"Vault file {vault_filepath} for password not found in playbooks directory, please create it first!")
            command = ["ansible-playbook", f"--vault-password-file={vault_filepath}", playbook_path, "--extra-vars", playbook_args]
        else:
            command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
                ip_addr_str_search = re.findall(r'isolated_env_ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
                if self.instanceState == "present" and ip_addr_str_search:
                    ip_addr_string = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
                    logging.info(f"IP address of new isolated instance is: {ip_addr_string[-1]}")
                    ti.xcom_push(key="iso_env_ip", value=ip_addr_string[-1])
        rc = process.poll()
        if rc == 0:
            logging.info(f'Iso instance managed successfully!')
        else:
            raise AirflowFailException("Failed to manage isolated environment!")
        

    def __init__(self,
                 dag,
                 instanceState = "present",
                 taskName = "create-iso-inst",
                 **kwargs):

        super().__init__(
            dag=dag,
            name=taskName,
            python_callable=self.start,
            **kwargs
        )
        self.instanceState = instanceState
