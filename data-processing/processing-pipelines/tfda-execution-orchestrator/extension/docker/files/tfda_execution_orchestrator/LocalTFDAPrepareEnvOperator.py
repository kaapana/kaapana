import os
import logging
import sys
import subprocess
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR


class LocalTFDAPrepareEnvOperator(KaapanaPythonBaseOperator):

    def start(self, ds, ti, **kwargs):
        logging.info("Prepare the Secure Processing Environment (SPE)...")
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        download_pkg_path = os.path.join(operator_dir, "downloaded_packages")
        
        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")

        platform_config = kwargs["dag_run"].conf["platform_config"]        
        request_config = kwargs["dag_run"].conf["request_config"]
        
        request_type = request_config["request_type"]
        platform_name = platform_config["default_platform"][request_type]
        flavor_name = platform_config["platforms"][platform_name]["default_flavor"][request_type]

        python_packages = request_config["python_packages"]
        if python_packages:
            requirements_filepath = os.path.join(playbooks_dir, "requirements.txt")
            with open(requirements_filepath, "w") as myfile:
                try:
                    myfile.write('\n'.join(str(package) for package in python_packages))
                except Exception as exc:
                    raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")
            print(f"Python package list: {python_packages}")

            prepare_env_playbook_path = os.path.join(playbooks_dir, "prepare_instance.yaml")
            if not os.path.isfile(prepare_env_playbook_path):
                raise AirflowFailException(f"Playbook '{prepare_env_playbook_path}' file not found!")

            # ssh_key_path = platform_config["platform_config"][platform_name]["platform_flavors"][flavor_name]["ssh_key_path"]
            ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["ssh_key_name"]
            remote_username = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["remote_username"]
            
            logging.debug("Downloading requested python packages and installing them offline into isolated environment...")
            playbook_args = f"target_host={iso_env_ip} ssh_key_name={ssh_key_name} remote_username={remote_username} requirements_filepath={requirements_filepath} download_pkg_path={download_pkg_path}"
            command = ["ansible-playbook", prepare_env_playbook_path, "--extra-vars", playbook_args]
            process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
            while True:
                output = process.stdout.readline()
                if process.poll() is not None:
                    break
                if output:
                    print(output.strip())
            rc = process.poll()
            if rc == 0:
                logging.info(f"Requested dependendencies successfully installed!! Cleaning up package downloads folder...")
                for package in os.scandir(download_pkg_path):
                    os.remove(package.path)
            else:
                raise AirflowFailException("FAILED to install requested packages! Cannot proceed further...")

        else:
            logging.debug("No additional packages were requested to be installed, skipping...")

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="prepare-env",
            python_callable=self.start,
            **kwargs
        )