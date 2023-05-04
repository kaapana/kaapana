from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

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
                "default": True,
                "readOnly": False,
                "required": True,
            }
        },
    }
}
args = {
    "ui_visible": False,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 3,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    dag_id="service-segmentation-thumbnail",
    default_args=args,
    concurrency=20,
    max_active_runs=30,
    schedule_interval=None,
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

generate_segmentation_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-segmentation-thumbnail",
    input_operator=get_input,
    orig_image_operator=get_ref_ct_series_from_seg,
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-thumbnail",
    zip_files=False,
    action="put",
    bucket_name="thumbnails",
    action_operators=[generate_segmentation_thumbnail],
    file_white_tuples=(".png"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
(
    get_input
    >> get_ref_ct_series_from_seg
    >> generate_segmentation_thumbnail
    >> put_to_minio
    >> clean
)
