from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from kaapana.operators.LaunchPodOperator import LaunchPodOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from datetime import datetime

import os

log = LoggingMixin().log

dag_info = {
    "visible": False,
}

args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='launch-app',
    default_args=args,
    schedule_interval=None)


launch_app = LaunchPodOperator(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag)

launch_app >> clean
