import logging
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalTriggerContainerIsolationOperator(KaapanaPythonBaseOperator):
    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        self.trigger_dag_id = "dag-tfda-execution-orchestrator"
        dag_run_id = generate_run_id(self.trigger_dag_id)
        logging.info("Triggering isolated execution orchestrator...")
        dag_config = kwargs["dag_run"].conf
        try:
            trigger(
                dag_id=self.trigger_dag_id,
                run_id=dag_run_id,
                conf=dag_config,
                replace_microseconds=False,
            )
        except Exception as e:
            logging.error(f"Error while triggering isolated workflow...")
            logging.error(e)
        dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
        if dag_run:
            logging.debug(
                f"The latest isolated workflow has been triggered at: {dag_run.execution_date}!!!"
            )
        dag_state = get_dag_run_state(
            dag_id=self.trigger_dag_id, execution_date=dag_run.execution_date
        )
        while dag_state["state"] != "failed" and dag_state["state"] != "success":
            dag_run = self.get_most_recent_dag_run(self.trigger_dag_id)
            dag_state = get_dag_run_state(
                dag_id=self.trigger_dag_id, execution_date=dag_run.execution_date
            )
        if dag_state["state"] == "failed":
            raise AirflowFailException(
                f"**************** The isolated workflow has FAILED ****************"
            )
        if dag_state["state"] == "success":
            logging.debug(
                f"**************** The isolated workflow was SUCCESSFUL ****************"
            )

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag,
            name="trigger-isolated-container-execution",
            python_callable=self.start,
            **kwargs,
        )
