import os
import logging
import subprocess
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalCopyDataAndAlgoOperator(KaapanaPythonBaseOperator):
    def start(self, ds, ti, **kwargs):
        logging.info("Copy data and algorithm to isolated environment...")
        workflow_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        )
        base_dir = os.path.dirname(workflow_dir)
        minio_path = os.path.join(base_dir, "minio")
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        playbooks_dir = os.path.join(operator_dir, "ansible_playbooks")
        playbook_path = os.path.join(
            playbooks_dir, "copy_data_and_algo_to_iso_env.yaml"
        )

        if not os.path.isfile(playbook_path):
            raise AirflowFailException(f"Playbook '{playbook_path}' file not found!")

        conf = kwargs["dag_run"].conf
        platform_config = conf["platform_config"]

        workflow_type = conf["workflow_type"]
        platform_name = platform_config["default_platform"][workflow_type]
        flavor_name = platform_config["platforms"][platform_name]["default_flavor"][
            workflow_type
        ]
        ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][
            flavor_name
        ]["ssh_key_name"]
        remote_username = platform_config["platforms"][platform_name][
            "platform_flavors"
        ][flavor_name]["remote_username"]
        user_selected_data = conf["bucket_id"]
        user_experiment_name = conf["experiment_name"]

        src_data_path = os.path.join(minio_path, user_selected_data)
        src_algorithm_files_path = os.path.join(
            operator_dir, "algorithm_files", workflow_type
        )

        iso_env_ip = ti.xcom_pull(key="iso_env_ip", task_ids="create-iso-inst")

        playbook_args = f"target_host={iso_env_ip} ssh_key_name={ssh_key_name} remote_username={remote_username} workflow_type={workflow_type} src_algorithm_files_path={src_algorithm_files_path} user_experiment_name={user_experiment_name} src_data_path={src_data_path} user_selected_data={user_selected_data}"
        command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc == 0:
            logging.info(f"Files copied successfully!!")
        else:
            raise AirflowFailException("Playbook FAILED! Cannot proceed further...")

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag, name="copy-data-algo", python_callable=self.start, **kwargs
        )
