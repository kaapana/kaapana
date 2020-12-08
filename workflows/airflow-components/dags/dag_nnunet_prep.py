from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator 

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-prep',
    default_args=args,
    concurrency=20,
    max_active_runs=20,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=get_input,
    output_type="nii.gz",
    seg_filter="liver",
    parallel_id='seg',
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(dag=dag, input_operator=get_input, search_policy="reference_uid", modality=None)
dcm2nifti_ct = DcmConverterOperator(dag=dag, input_operator=get_ref_ct_series_from_seg, parallel_id='ct', output_format='nii.gz')
put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[dcm2nifti_seg,dcm2nifti_ct,], bucket_name="nnunet-prep", file_white_tuples=('.nii.gz'),zip_files=False)
clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> put_to_minio
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> put_to_minio >> clean
