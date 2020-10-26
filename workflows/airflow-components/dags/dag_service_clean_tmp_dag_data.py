from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from kaapana.operators.LocalCleanUpExpiredWorkflowDataOperator import LocalCleanUpExpiredWorkflowDataOperator

from datetime import timedelta
from datetime import datetime

import os

log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='service-clean-up-expired-workflow-data',
    default_args=args,
    schedule_interval='@daily',
    concurrency=5,
    max_active_runs=1
)

clean_up = LocalCleanUpExpiredWorkflowDataOperator(dag=dag, expired_period=timedelta(days=14))

clean_up
