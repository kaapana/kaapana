import glob
import json
import os
from datetime import timedelta
from pathlib import Path

import requests
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmValidatorOperator import DcmValidatorOperator
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalAssignDataToProjectOperator import (
    LocalAssignDataToProjectOperator,
)
from kaapana.operators.LocalAutoTriggerOperator import LocalAutoTriggerOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalDcmBranchingOperator import LocalDcmBranchingOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalRemoveDicomTagsOperator import LocalRemoveDicomTagsOperator
from kaapana.operators.LocalValidationResult2MetaOperator import (
    LocalValidationResult2MetaOperator,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapanapy.helper import get_minio_client
from kaapanapy.helper.HelperOpensearch import DicomTags
from kaapanapy.settings import KaapanaSettings

args = {
    "ui_visible": False,
    "owner": "system",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
}


dag = DAG(
    dag_id="service-process-incoming-dcm",
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=["service"],
)

get_input = LocalGetInputDataOperator(dag=dag, delete_input_on_success=True)

remove_tags = LocalRemoveDicomTagsOperator(dag=dag, input_operator=get_input)
auto_trigger_operator = LocalAutoTriggerOperator(dag=dag, input_operator=get_input)

dcm_send = LocalDicomSendOperator(
    dag=dag,
    input_operator=get_input,
)

extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=get_input)

add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)

assign_to_project = LocalAssignDataToProjectOperator(
    dag=dag, input_operator=extract_metadata
)

push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=get_input, json_operator=extract_metadata
)

validate = DcmValidatorOperator(
    dag=dag,
    input_operator=get_input,
    exit_on_error=False,
)

save_to_meta = LocalValidationResult2MetaOperator(
    dag=dag,
    input_operator=extract_metadata,
    validator_output_dir=validate.operator_out_dir,
    validation_tag="00111001",
    apply_project_context=True,
    index_to_default_project=True,
)

put_html_to_minio = LocalMinioOperator(
    dag=dag,
    action_operator_dirs=[validate.operator_out_dir],
    json_operator=extract_metadata,
    target_dir_prefix="staticwebsiteresults",
    name="put-results-html-to-minio",
    action="put",
    file_white_tuples=(".html"),
)


def fetch_bucket_name_and_put_html_to_minio_admin_bucket(ds, **kwargs):
    # Fetch the Project Bucket name and store the validation results
    # html file if the project is not a admin project

    kaapana_settings = KaapanaSettings()
    minio = get_minio_client()

    target_dir_prefix = "staticwebsiteresults"

    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / extract_metadata.operator_out_dir
        json_files = [f for f in json_dir.glob("*.json")]
        assert len(json_files) == 1
        metadata_file = json_files[0]
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        project_name = metadata.get(DicomTags.clinical_trial_protocol_id_tag)

        validator_results_dir = Path(batch_element_dir) / validate.operator_out_dir
        result_files = [f for f in validator_results_dir.glob("*.html")]

        if len(result_files) > 0 and project_name != "admin":
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            response.raise_for_status()

            project = response.json()

            root_path = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id
            for file_path in result_files:
                object_path = (
                    f"{target_dir_prefix}/{str(file_path.relative_to(root_path))}"
                )
                minio.fput_object(
                    bucket_name=project.get("s3_bucket"),
                    object_name=object_path,
                    file_path=file_path,
                )


# Task to put the validation results in minio admin bucket for non-admin projects
put_results_html_to_minio_admin_bucket = KaapanaPythonBaseOperator(
    name="put-results-html-to-minio-admin-bucket",
    python_callable=fetch_bucket_name_and_put_html_to_minio_admin_bucket,
    dag=dag,
)

get_ref_ct_series = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
)


def has_ref_series(ds) -> bool:
    return ds.Modality in ["SEG", "RTSTRUCT"]


branch_by_has_ref_series = LocalDcmBranchingOperator(
    dag=dag,
    name="branch-has-ref",
    input_operator=get_input,
    condition=has_ref_series,
    branch_true_operator="get-ref-series-ct",
    branch_false_operator="generate-thumbnail",
)
generate_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-thumbnail",
    input_operator=get_input,
    get_ref_series_operator=get_ref_ct_series,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    # dev_server="code-server",
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

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)

get_input >> auto_trigger_operator
get_input >> [extract_metadata]
extract_metadata >> [
    push_json,
    add_to_dataset,
    assign_to_project,
    remove_tags,
]

(
    push_json
    >> validate
    >> save_to_meta
    >> put_html_to_minio
    >> put_results_html_to_minio_admin_bucket
    >> clean
)
(remove_tags >> dcm_send)

(push_json >> branch_by_has_ref_series >> get_ref_ct_series)

save_to_meta >> generate_thumbnail
get_ref_ct_series >> generate_thumbnail >> put_thumbnail_to_project_bucket

(branch_by_has_ref_series >> generate_thumbnail)

[
    push_json,
    add_to_dataset,
    assign_to_project,
    dcm_send,
    put_html_to_minio,
    put_thumbnail_to_project_bucket,
] >> clean
