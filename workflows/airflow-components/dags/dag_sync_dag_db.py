from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from kaapana.operators.LocalRemoveDeletedDagsFromDB import LocalRemoveDeletedDagsFromDB

from datetime import timedelta
from datetime import datetime

import os

log = LoggingMixin().log

dag_info = {
    "visible": False,
}

args = {
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='sync-dags-with-db',
    default_args=args,
    schedule_interval="@hourly")

remove_delete_dags = LocalRemoveDeletedDagsFromDB(dag=dag)

remove_delete_dags
