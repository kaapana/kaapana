from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalServiceSyncDagsDbOperator import LocalServiceSyncDagsDbOperator
from datetime import timedelta
log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'system',
    'depends_on_past': False,
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(minutes=1)
}

dag = DAG(
    dag_id='service-sync-dags-with-db',
    default_args=args,
    schedule_interval="@daily",
    start_date=args["start_date"],
    concurrency=1,
    max_active_runs=1,
    tags=['service']
)

remove_delete_dags = LocalServiceSyncDagsDbOperator(dag=dag)

remove_delete_dags
