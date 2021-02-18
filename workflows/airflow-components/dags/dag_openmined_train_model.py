from airflow.models import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin

from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator

from openmined.OpenminedTrainModelOperator import OpenminedTrainModelOperator


# set grid information
GRID_HOST = '10.128.129.76'
GRID_PORT = '7000'

log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='openmined-train-model',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
    )

train_model = OpenminedTrainModelOperator(dag=dag, grid_host=GRID_HOST, grid_port=GRID_PORT)

train_model #>> clean