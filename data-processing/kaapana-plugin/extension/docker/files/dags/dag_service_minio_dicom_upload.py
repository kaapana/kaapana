from kaapana.operators.LocalMinioOperator import LocalMinioOperator

from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import DAG
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from datetime import timedelta


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'system',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='service-minio-dicom-upload',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5,
    tags=['service']
)

get_object_from_minio = LocalMinioOperator(
    dag=dag,
    # action_operator_dirs=['dicoms'],
    file_white_tuples=('.zip'),
    operator_out_dir='dicoms'
)

unzip_files = ZipUnzipOperator(
    dag=dag,
    input_operator=get_object_from_minio,
    batch_level=True,
    mode="unzip"
)

dicom_send = DcmSendOperator(
    dag=dag,
    input_operator=unzip_files,
    ae_title='uploaded',
    level='batch'
)

remove_object_from_minio = LocalMinioOperator(
    dag=dag,
    parallel_id='removing',
    action='remove',
    file_white_tuples=('.zip'),
    trigger_rule=TriggerRule.ALL_DONE
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True
)

get_object_from_minio >> unzip_files >> dicom_send >> remove_object_from_minio >> clean
