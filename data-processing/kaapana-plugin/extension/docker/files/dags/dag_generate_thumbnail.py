from datetime import timedelta

import glob
import json
import os
from pathlib import Path

import requests
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapanapy.helper import get_minio_client
from kaapanapy.settings import KaapanaSettings
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.CheckCompletnessOperator import CheckCompletenessOperator
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalDcmBranchingOperator import LocalDcmBranchingOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from airflow.utils.trigger_rule import TriggerRule

ui_forms = {
    "workflow_form": {
        "type": "object",
    }
}

log = LoggingMixin().log

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(dag_id="generate-thumbnail", default_args=args, schedule_interval=None)
get_input = GetInputOperator(dag=dag)
extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=get_input)
check_completeness = CheckCompletenessOperator(
    dag=dag,
    name="check-completeness",
    input_operator=get_input,
)


def has_ref_series(ds) -> bool:
    return ds.Modality in ["SEG", "RTSTRUCT"]


branch_by_has_ref_series = LocalDcmBranchingOperator(
    dag=dag,
    input_operator=get_input,
    condition=has_ref_series,
    branch_true_operator="get-ref-series-ct",
    branch_false_operator="generate-thumbnail",
)

get_ref_ct_series = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
)

generate_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-thumbnail",
    input_operator=get_input,
    get_ref_series_operator=get_ref_ct_series,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)


def upload_thumbnails_into_project_bucket(ds, **kwargs):
    """
    Uploads the generated thumbnails to the project bucket,
    where project is determined from the "00120020 ClinicalTrialProtocolID_keyword" tag of the dicom metadata.
    Additionally uploads the thumbnails to the project bucket of the admin project.
    """

    kaapana_settings = KaapanaSettings()
    minio = get_minio_client()

    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / extract_metadata.operator_out_dir
        thumbnail_dir = Path(batch_element_dir) / generate_thumbnail.operator_out_dir

        json_files = [f for f in json_dir.glob("*.json")]
        assert len(json_files) == 1
        metadata_file = json_files[0]
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        project_name = metadata.get("00120020 ClinicalTrialProtocolID_keyword")
        response = requests.get(
            f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/{project_name}"
        )
        project = response.json()
        thumbnails = [f for f in thumbnail_dir.glob("*.png")]
        assert len(thumbnails) == 1
        thumbnail_path = thumbnails[0]
        series_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
        minio_object_path = f"thumbnails/{series_uid}.png"
        minio.fput_object(
            bucket_name=project.get("s3_bucket"),
            object_name=minio_object_path,
            file_path=thumbnail_path,
        )

        if project_name != "admin":
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            project = response.json()
            minio.fput_object(
                bucket_name=project.get("s3_bucket"),
                object_name=minio_object_path,
                file_path=thumbnail_path,
            )


put_thumbnail_to_project_bucket = KaapanaPythonBaseOperator(
    name="thumbnail_to_project_bucket",
    python_callable=upload_thumbnails_into_project_bucket,
    dag=dag,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> [extract_metadata, check_completeness]

(
    extract_metadata
    >> check_completeness
    >> branch_by_has_ref_series
    >> get_ref_ct_series
    >> generate_thumbnail
    >> put_thumbnail_to_project_bucket
    >> clean
)
(branch_by_has_ref_series >> generate_thumbnail)
