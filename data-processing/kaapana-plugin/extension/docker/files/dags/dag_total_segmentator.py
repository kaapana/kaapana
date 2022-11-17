from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetTotalSegmentatorModelsOperator import LocalGetTotalSegmentatorModelsOperator
from kaapana.operators.TotalSegmentatorOperator import TotalSegmentatorOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalCombineMasksOperator import LocalCombineMasksOperator
from kaapana.operators.PyRadiomicsOperator import PyRadiomicsOperator

max_active_runs = 10
concurrency = max_active_runs * 2
default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1

ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "TotalSegmentator: robust segmentation of 104 anatomical structures in CT images",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Wasserthal J., Meyer M., Breit H., Cyriac J., Yang S., Segeroth M.",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/2208.05868",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": True,
            },
            "task": {
                "title": "Task",
                "default": "total",
                "description": "total",  # , lung_vessels, cerebral_bleed, hip_implant, coronary_arteries
                "enum": ["total"],  # , "lung_vessels", "cerebral_bleed", "hip_implant", "coronary_arteries
                "type": "string",
                "readOnly": False,
                "required": True
            }
        }
    }
}
args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='total-segmentator',
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_total_segmentator_model = LocalGetTotalSegmentatorModelsOperator(
    dag=dag
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format='nii.gz',
)

total_segmentator = TotalSegmentatorOperator(
    dag=dag,
    input_operator=dcm2nifti
)

combine_masks = LocalCombineMasksOperator(
    dag=dag,
    input_operator=total_segmentator
)

alg_name = 'TotalSegmentator'
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=combine_masks,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    multi_label_seg_info_json='seg_info.json',
    skip_empty_slices=True,
    alg_name=alg_name,
)

pyradiomics = PyRadiomicsOperator(
    dag=dag,
    input_operator=dcm2nifti,
    segmentation_operator=total_segmentator,
)

put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[pyradiomics], file_white_tuples=('.json'))
dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_total_segmentator_model >> total_segmentator
get_input >> dcm2nifti >> total_segmentator >> combine_masks >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
total_segmentator >> pyradiomics >> put_to_minio >> clean
