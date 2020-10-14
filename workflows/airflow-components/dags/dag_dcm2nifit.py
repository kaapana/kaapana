from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log


args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='dcm2nifti',
    default_args=args,
    concurrency=20,
    max_active_runs=10,
    schedule_interval=None
    )


get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, output_format='nii.gz')
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> convert >>  clean
