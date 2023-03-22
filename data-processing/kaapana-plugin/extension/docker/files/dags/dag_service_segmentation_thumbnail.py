from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalCombineMasksOperator import LocalCombineMasksOperator

max_active_runs = 10
concurrency = max_active_runs * 2

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": True,
                "readOnly": False,
                "required": True,
            }
        },
    }
}
args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
}

dag = DAG(
    dag_id="service-segmentation-thumbnail",
    default_args=args,
    schedule_interval=None,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    tags=["service"],
)

get_input = LocalGetInputDataOperator(
    dag=dag, check_modality=True, parallel_downloads=5
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
)

dcm2nifti_seg = Mask2nifitiOperator(
    dag=dag, dicom_operator=get_ref_ct_series_from_seg, input_operator=get_input
)

combine_masks = LocalCombineMasksOperator(dag=dag, input_operator=dcm2nifti_seg)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag, input_operator=get_ref_ct_series_from_seg, output_format="nii.gz"
)

generate_segmentation_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-segmentation-thumbnail",
    input_operator=combine_masks,
    orig_image_operator=dcm2nifti_ct,
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-thumbnail",
    zip_files=False,
    action="put",
    action_operators=[generate_segmentation_thumbnail],
    file_white_tuples=(".png"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
(
    get_input
    >> get_ref_ct_series_from_seg
    >> dcm2nifti_seg
    >> combine_masks
    >> generate_segmentation_thumbnail
)
(
    get_input
    >> get_ref_ct_series_from_seg
    >> dcm2nifti_ct
    >> generate_segmentation_thumbnail
    >> put_to_minio
    >> clean
)
