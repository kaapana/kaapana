from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from kaapana.operators.LocalServiceSyncDagsDbOperator import LocalServiceSyncDagsDbOperator

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
    dag_id='service-sync-dags-with-db',
    default_args=args,
    schedule_interval="@hourly",
    concurrency=1,
    max_active_runs=1
)

remove_delete_dags = LocalServiceSyncDagsDbOperator(dag=dag)

remove_delete_dags
