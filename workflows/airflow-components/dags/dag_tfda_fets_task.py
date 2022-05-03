from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from airflow.operators.python_operator import PythonOperator

from tfda_execution_orchestrator.LocalFeTSSubmissions import LocalFeTSSubmissions
from tfda_execution_orchestrator.LocalFeTSTest import LocalFeTSTest

log = LoggingMixin().log

from datetime import datetime, timedelta

args = {
    "depends_on_past": False,
    "start_date": datetime(2022, 5, 7, 00, 00),
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
    # schedule_interval="0 0 1 * *",
)


evaluate_submissions = LocalFeTSSubmissions(dag=dag)
test = LocalFeTSTest(dag=dag)

evaluate_submissions >> test
