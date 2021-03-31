from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin

from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='service-minio-action',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
    )

reload_models_from_minio = LocalMinioOperator(
    dag=dag,
    action='get', # action='put',
    run_dir='/models',
    bucket_name='models'
    )

cleanup = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True
    )
 
reload_models_from_minio >> cleanup