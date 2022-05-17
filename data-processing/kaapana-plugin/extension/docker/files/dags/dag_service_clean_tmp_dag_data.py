from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalCleanUpExpiredWorkflowDataOperator import LocalCleanUpExpiredWorkflowDataOperator
from kaapana.operators.LocalCtpQuarantineCheckOperator import LocalCtpQuarantineCheckOperator
from datetime import timedelta


START_DATE = days_ago(1)
log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'system',
    'depends_on_past': False,
    'start_date': START_DATE,
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='service-cleanup-tmp-data',
    default_args=args,
    schedule_interval='@daily',
    start_date=START_DATE,
    concurrency=5,
    max_active_runs=1,
    tags=['service']
)

clean_up = LocalCleanUpExpiredWorkflowDataOperator(dag=dag, expired_period=timedelta(days=14))
check_ctp_quarantine = LocalCtpQuarantineCheckOperator(dag=dag)

clean_up
check_ctp_quarantine