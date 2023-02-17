from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
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
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='create-segmentation-thumbnails',
    default_args=args,
    schedule_interval=None,
    tags=['service']
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    check_modality=True,
    parallel_downloads=5
)

dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=get_input,
    output_format="nii.gz",
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_ref_ct_series_from_seg,
    output_format='nii.gz'
)

generate_segmentation_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name='generate-segmentation-thumbnail',
    input_operator=dcm2nifti_seg,
    orig_image_operator=dcm2nifti_ct
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name='upload-thumbnail',
    zip_files=False,
    action='put',
    action_operators=[generate_segmentation_thumbnail],
    file_white_tuples=('.png')
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
get_input >> dcm2nifti_seg >> generate_segmentation_thumbnail
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> generate_segmentation_thumbnail >> put_to_minio >> clean
