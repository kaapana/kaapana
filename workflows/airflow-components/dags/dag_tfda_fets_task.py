from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.models import Variable
from airflow.operators.bash_operator import BashOperator
from tfda_execution_orchestrator.LocalFeTSSubmissions import LocalFeTSSubmissions
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from datetime import datetime, timedelta

log = LoggingMixin().log

args = {
    "depends_on_past": False,
    "start_date": datetime(2022, 4, 26, 00, 00),
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
    "catchup": False,
}

# Instantiate a DAG my_dag that runs every day
# DAG objects contain tasks
# Time is in UTC!!!
dag = DAG(
    dag_id="dag-tfda-fets-task",
    default_args=args,
    ## TODO clarify frequency for scheduler
    # schedule_interval="0 0 1 * *",
)

evaluate_submissions = LocalFeTSSubmissions(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

evaluate_submissions >> clean
