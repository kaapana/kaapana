import os
import json
import logging
import subprocess
from subprocess import PIPE
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

class LocalTriggerContainerIsolationOperator(KaapanaPythonBaseOperator):    
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
    
    
    def load_config(self, config_filepath):
        with open(config_filepath, "r") as stream:
            try:
                config_dict = json.load(stream)
                return config_dict
            except Exception as exc:
                raise AirflowFailException(f"Could not extract configuration due to error: {exc}!!")

    
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        operator_dir = os.path.dirname(os.path.abspath(__file__))
        platform_config_path = os.path.join(operator_dir, "platform_specific_config", "platform_config.json")
        logging.info("Loading platform specific configuration...")
        platform_config = self.load_config(platform_config_path)
        
        self.trigger_dag_id = "dag-tfda-execution-orchestrator"
        # self.dag_run_id = kwargs['dag_run'].run_id       
        self.conf = kwargs['dag_run'].conf
        self.conf["platform_config"] = platform_config
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
            name="trigger-isolated-container-execution",
            python_callable=self.start,
            **kwargs
        )
        