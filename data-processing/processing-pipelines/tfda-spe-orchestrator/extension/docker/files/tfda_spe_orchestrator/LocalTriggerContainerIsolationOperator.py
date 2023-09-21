import logging
from airflow.exceptions import AirflowFailException
from airflow.models import DagRun
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.api.common.experimental.get_dag_run_state import get_dag_run_state
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


class LocalTriggerContainerIsolationOperator(KaapanaPythonBaseOperator):
    """
    Custom operator for triggering an containerized workflow in a Secure Processing Environment (SPE).

    This operator extends the KaapanaPythonBaseOperator and is designed to trigger a separate DAG
    (tfda-spe-orchestrator) that executes a containerized workflow in an SPE. It leverages
    the Airflow API to trigger the specified DAG with a custom configuration, waits for the DAG
    to complete execution, and checks the final state of the isolated workflow.

    Notes:
        1. This operator triggers the 'tfda-spe-orchestrator' DAG with a custom configuration.
        2. The 'start' method handles the triggering, monitoring, and checking of the isolated workflow's state.
        3. If the isolated workflow execution fails, the operator raises an AirflowFailException.
        4. Ensure that the 'tfda-spe-orchestrator' DAG exists and is correctly configured before using this operator.
    """

    def get_most_recent_dag_run(self, dag_id):
        dag_runs = DagRun.find(dag_id=dag_id)
        dag_runs.sort(key=lambda x: x.execution_date, reverse=True)
        return dag_runs[0] if dag_runs else None

    def start(self, ds, ti, **kwargs):
        self.trigger_dag_id = "tfda-spe-orchestrator"
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
            logging.info(
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
            logging.info(
                f"**************** The isolated workflow was SUCCESSFUL ****************"
            )

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag,
            name="trigger-isolated-container-execution",
            python_callable=self.start,
            **kwargs,
        )
