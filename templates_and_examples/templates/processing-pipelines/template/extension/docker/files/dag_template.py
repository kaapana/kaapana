from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta

from airflow.models import DAG

from templates.TemplateExecBashOperator import TemplateExecBashOperator
from templates.TemplateExecPythonOperator import TemplateExecPythonOperator

from datetime import datetime

log = LoggingMixin().log


args = {
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="dag-template",
    default_args=args,
    max_active_runs=5,
    concurrency=5,
    schedule_interval=None,
)

bash_operator = TemplateExecBashOperator(dag=dag)
python_operator = TemplateExecPythonOperator(dag=dag)

bash_operator >> python_operator
