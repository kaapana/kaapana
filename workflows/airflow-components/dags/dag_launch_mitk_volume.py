from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.KaapanaApplicationBaseOperator import KaapanaApplicationBaseOperator

from datetime import datetime

import os

log = LoggingMixin().log

args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='launch-mitk-volume',
    default_args=args,
    schedule_interval=None)

get_input = LocalGetInputDataOperator(dag=dag)
launch_app = KaapanaApplicationBaseOperator(dag=dag, chart_name='mitk-volume-chart', version='0.1-vdev')
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> launch_app >> clean
