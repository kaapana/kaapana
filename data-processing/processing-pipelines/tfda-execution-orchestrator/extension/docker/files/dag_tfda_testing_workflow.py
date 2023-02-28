from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.models import DAG
from tfda_execution_orchestrator.LocalTFDATestingOperator import LocalTFDATestingOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from datetime import timedelta

log = LoggingMixin().log

args = {
    "start_date": "2022-07-12",
    "retries": 0,
    "retry_delay": timedelta(minutes=10),
    "catchup": False,
}

dag = DAG(
    dag_id="dag-tfda-testing-workflow",
    default_args=args,
    # schedule_interval="@daily",
    schedule_interval=None,
)

tfda_testing = LocalTFDATestingOperator(dag=dag, execution_timeout=timedelta(hours=24))
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

tfda_testing >> clean
