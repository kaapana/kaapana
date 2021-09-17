from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nndetection.NnDetectionOperator import NnDetectionOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

max_active_runs = 10
concurrency = max_active_runs * 2
default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "ntta": {
                "title": "NTTA",
                "default": "1",
                "description": "NTTA",
                "enum": ["1", "4", "8"],
                "type": "string",
                "readOnly": False,
                "required": True
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            }
        }
    }
}
args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nndetect-inference',
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format='nii.gz'
)

nndetection_predict = NnDetectionOperator(
    dag=dag,
    mode="inference",
    input_operator=dcm2nifti,
    input_modality_operators=[dcm2nifti],
    inf_preparation=True,
    inf_threads_prep=2,
    inf_threads_nifti=2
)

alg_name = "nndetection"

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nndetection_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    skip_empty_slices=True,
    alg_name=alg_name
)

dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2nifti >> nndetection_predict >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
