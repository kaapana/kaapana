import os
import json
import logging
#import yaml
import subprocess
from subprocess import PIPE
from datetime import datetime
from asyncore import write
from pathlib import Path
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

class LocalTFDATestingOperator(KaapanaPythonBaseOperator):    
    def run_command(self, command):
        process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print(output.strip())
        return_code = process.poll()
        return return_code
    
    
    def load_config(self, config_filepath, format):
        with open(config_filepath, "r") as stream:
            try:
                if format == "json":
                    config_dict = json.load(stream)
                ## TODO: yaml is out of request now, so commenting out,, can be removed later
                #elif format == "yaml":
                    #config_dict = yaml.safe_load(stream)
                return config_dict
            except Exception as exc:
                raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")
    
    def extract_info_from_request(self, request_config):
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        user_algorithm_path = os.path.join(operator_dir, "algorithm_files", request_config["request_type"], request_config["user_selected_algorithm"])
        Path(user_algorithm_path).mkdir(parents=True, exist_ok=True)
        if request_config["request_type"] == "shell_execute":            
            bash_script_path = os.path.join(user_algorithm_path, "user_input_commands.sh")
            # os.path.exists(bash_script_path)
            with open(bash_script_path, "w") as stream:
                stream.write(request_config["bash_string"])
        elif request_config["request_type"] == "container_workflow":
            logging.debug("Downloading container from registry since container workflow is requested...")
            logging.info("Logging into container registry!!!") 
            command = ["skopeo", "login", "--username", f"{request_config['container']['username']}", "--password", f"{request_config['container']['password']}", f"{request_config['container']['registry_url']}"]
            return_code = self.run_command(command=command)
            if return_code == 0:
                logging.info(f"Login to the registry successful!!")
            else:
                raise AirflowFailException("Login to the registry FAILED! Cannot proceed further...")

            logging.debug(f"Pulling container: {request_config['container']['name']}:{request_config['container']['version']}...")
            tarball_file = os.path.join(user_algorithm_path, f"{request_config['user_selected_algorithm']}.tar")
            if os.path.exists(tarball_file):
                logging.debug(f"Submission tarball already exists locally... deleting it now to pull latest!!")
                os.remove(tarball_file)
            ## Due to absense of /etc/containers/policy.json in Airflow container, following Skopeo command only works with "--insecure-policy"
            command2 = ["skopeo", "--insecure-policy", "copy", f"docker://{request_config['container']['registry_url']}/{request_config['container']['name']}:{request_config['container']['version']}", f"docker-archive:{tarball_file}", "--additional-tag", f"{request_config['container']['name']}:{request_config['container']['version']}"]
            return_code2 = self.run_command(command=command2)
            if return_code2 != 0:
                raise AirflowFailException(f"Error while trying to download container! Exiting...")        
        else:
            raise AirflowFailException(f"Workflow type {request_config['request_type']} not supported yet! Exiting...")

    
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        platform_config_path = os.path.join(operator_dir, "platform_specific_configs", "platform_config.json")
        #request_config_path = os.path.join(operator_dir, "request_specific_configs", "request_config.yaml")
        
        logging.info("Loading platform and request specific configurations...")
        platform_config = self.load_config(platform_config_path, "json")
        #request_config = self.load_config(request_config_path, "yaml")
        self.extract_info_from_request(request_config)
        
        self.trigger_dag_id = "dag-tfda-execution-orchestrator"
        # self.dag_run_id = kwargs['dag_run'].run_id
        self.conf = kwargs['dag_run'].conf
        self.conf["platform_config"] = platform_config
        self.conf["request_config"] = request_config
        dag_run_id = generate_run_id(self.trigger_dag_id)
        logging.info("Triggering isolated execution orchestrator...")
        try:
            trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                            replace_microseconds=False)
        except Exception as e:
            logging.error(f"Error while triggering isolated workflow...")
            logging.error(e)

        dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
        if dag_run:
            logging.debug(f"The latest isolated workflow has been triggered at: {dag_run.execution_date}!!!")

        dag_state = get_dag_run_state(dag_id=self.trigger_dag_id, execution_date=dag_run.execution_date)

        while dag_state["state"] != "failed" and dag_state['state'] != "success":
            dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
            dag_state = get_dag_run_state(dag_id=self.trigger_dag_id, execution_date=dag_run.execution_date)                        

        if dag_state["state"] == "failed":
            logging.debug(f"**************** The evaluation has FAILED ****************")
        if dag_state["state"] == "success":
            logging.debug(f"**************** The evaluation was SUCCESSFUL ****************")


    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="tfda-testing",
            python_callable=self.start,
            **kwargs
        )
        