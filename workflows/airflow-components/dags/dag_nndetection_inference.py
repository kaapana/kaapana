from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nndetection.NnDetectionOperator import NnDetectionOperator
from nndetection.LocalResultSplitterOperator import LocalResultSplitterOperator
from kaapana.operators.Json2DcmSROperator import Json2DcmSROperator
from kaapana.operators.DcmModifyOperator import DcmModifyOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
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

result_orga = LocalResultSplitterOperator(
    dag=dag,
    input_operator=nndetection_predict
)

put_radiomics_to_minio = LocalMinioOperator(
    dag=dag,
    action='put',
    action_operators=[result_orga],
    file_white_tuples=('.json')
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

# json2dicomSR = Json2DcmSROperator(
#     dag=dag,
#     input_operator=result_orga,
#     src_dicom_operator=get_input,
#     seg_dicom_operator=nrrd2dcmSeg_multi
# )

# dcmModify = DcmModifyOperator(
#     dag=dag,
#     input_operator=json2dicomSR,
#     dicom_tags_to_modify="(0008,0016)=1.2.840.10008.5.1.4.1.1.88.11"
# )
# dcmseg_send_sr = DcmSendOperator(dag=dag, input_operator=json2dicomSR, parallel_id="sr")

dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2nifti >> nndetection_predict >> result_orga >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
result_orga >> put_radiomics_to_minio >> clean
# result_orga >> json2dicomSR
# nrrd2dcmSeg_multi >> json2dicomSR >> dcmModify >> dcmseg_send_sr >> clean
