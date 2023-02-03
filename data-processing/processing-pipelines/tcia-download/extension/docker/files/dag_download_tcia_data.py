from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import DAG
from datetime import timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator

from tcia_download.TciaDownloadOperator import TciaDownloadOperator

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='service-tcia-download',
    default_args=args,
    schedule_interval=None
)

get_tcia_file_from_minio = LocalMinioOperator(
    dag=dag,
    action_operator_dirs=['dicoms'],
    file_white_tuples=('.tcia'),
    operator_out_dir='dicoms'
)

tcia_download = TciaDownloadOperator(
    dag=dag, 
    input_operator=get_tcia_file_from_minio,
    image_pull_policy="Always"
)

dicom_send = DcmSendOperator(
    dag=dag,
    input_operator=tcia_download,
    ae_title='tcia-download',
    level='batch'
)

remove_object_from_minio = LocalMinioOperator(
    dag=dag,
    parallel_id='removing',
    action='remove',
    file_white_tuples=('.tcia'),
    trigger_rule=TriggerRule.ALL_DONE
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, 
    clean_workflow_dir=True
)

get_tcia_file_from_minio >> tcia_download >> dicom_send >> remove_object_from_minio >> clean