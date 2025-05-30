import glob
import json
import os
from datetime import timedelta
from pathlib import Path

import requests
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDcmBranchingOperator import LocalDcmBranchingOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapanapy.helper import get_minio_client
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.settings import KaapanaSettings

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
get_dcm_input = GetInputOperator(dag=dag, name="get-dcm-input", data_type="dicom")
get_json_input = GetInputOperator(dag=dag, name="get-json-input", data_type="json")


def has_ref_series(ds) -> bool:
    return ds.Modality in ["SEG", "RTSTRUCT"]


branch_by_has_ref_series = LocalDcmBranchingOperator(
    dag=dag,
    input_operator=get_dcm_input,
    condition=has_ref_series,
    branch_true_operator="get-ref-series-ct",
    branch_false_operator="generate-thumbnail",
)

get_ref_ct_series = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_dcm_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
)

generate_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-thumbnail",
    input_operator=get_dcm_input,
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
        json_dir = Path(batch_element_dir) / get_json_input.operator_out_dir
        thumbnail_dir = Path(batch_element_dir) / generate_thumbnail.operator_out_dir

        json_files = [f for f in json_dir.glob("*.json")]
        assert len(json_files) == 1
        metadata_file = json_files[0]
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        project_name = metadata.get(DicomTags.clinical_trial_protocol_id_tag)
        series_uid = metadata.get(DicomTags.series_uid_tag)

        response = requests.get(
            f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects"
        )
        project = [
            project for project in response.json() if project["name"] == project_name
        ][0]
        thumbnails = [f for f in thumbnail_dir.glob("*.png")]
        assert len(thumbnails) == 1
        thumbnail_path = thumbnails[0]
        minio_object_path = f"thumbnails/{series_uid}.png"
        minio.fput_object(
            bucket_name=project.get("s3_bucket"),
            object_name=minio_object_path,
            file_path=thumbnail_path,
        )
        if project["name"] != "admin":
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            admin_project = response.json()
            minio.fput_object(
                bucket_name=admin_project.get("s3_bucket"),
                object_name=minio_object_path,
                file_path=thumbnail_path,
            )


put_thumbnail_to_project_bucket = KaapanaPythonBaseOperator(
    name="thumbnail_to_project_bucket",
    python_callable=upload_thumbnails_into_project_bucket,
    dag=dag,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
(
    get_dcm_input
    >> get_json_input
    >> branch_by_has_ref_series
    >> get_ref_ct_series
    >> generate_thumbnail
    >> put_thumbnail_to_project_bucket
    >> clean
)
(branch_by_has_ref_series >> generate_thumbnail)
