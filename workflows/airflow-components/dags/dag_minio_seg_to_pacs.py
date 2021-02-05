from mitk_minio_pacs_interaction.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from datetime import timedelta
from airflow.models import DAG


log = LoggingMixin().log

args = {
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='minio-seg-to-pacs',
    default_args=args,
    schedule_interval=None)

#predefine the bucketname and segmentation folder
bucket_name='pacs-dicom-data'
upload_folder_tree = 'segmentation_tree'

pull_object_from_minio = LocalMinioOperator(dag=dag, bucket_name=bucket_name, action_operator_dirs=[upload_folder_tree],
                                                  operator_out_dir=upload_folder_tree, file_white_tuples='.dcm', split_level=1)
dicom_send = DcmSendOperator(dag=dag, input_operator=pull_object_from_minio, ae_title='mitk-seg', level='pile')
clean = LocalWorkflowCleanerOperator(dag=dag)

pull_object_from_minio >> dicom_send >> clean