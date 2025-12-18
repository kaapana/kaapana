import glob
import json
import os
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import requests
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import (
    AIRFLOW_WORKFLOW_DIR,
    BATCH_NAME,
    SERVICES_NAMESPACE,
)
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
    dag=dag, input_operator=get_input, exit_on_error=False, namespace=SERVICES_NAMESPACE
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

get_ref_ct_series = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=branch_by_has_ref_series,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
)

generate_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-thumbnail",
    input_operator=get_input,
    get_ref_series_operator=get_ref_ct_series,
    trigger_rule=TriggerRule.ALL_DONE,
    namespace=SERVICES_NAMESPACE,
    # dev_server="code-server",
)


def upload_series_to_data_api(ds, **kwargs):
    """
    Creates entities in the data-api for each series and uploads metadata and thumbnails.

    This method:
    1. For each series creates an entity and adds the DICOM metadata to the data-api
    2. For each series where a thumbnail is produced, uploads the thumbnail as an artifact
    """

    skip = False  # Set to false to enable uploading to data-api
    if skip:
        print(
            "This is a demo operator showcasing the new and experimental Data API.\n"
            "Currently nothing happens since the operator is in skip mode.\n"
            "If you want to try the new feature, open dag_service_process_incoming_dcm.py "
            "in code server for airflow and set skip to False."
        )
        return

    kaapana_settings = KaapanaSettings()
    data_api_url = f"http://data-api.{kaapana_settings.services_namespace}.svc/v1"

    # Register the DICOM metadata schema if not already registered
    dicom_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "DICOM Metadata",
        "description": "DICOM metadata extracted from DICOM files",
        "additionalProperties": True,
    }

    try:
        response = requests.post(
            f"{data_api_url}/metadata/keys/dicom-series",
            json=dicom_schema,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        print("Successfully registered DICOM metadata schema")
    except requests.exceptions.RequestException as e:
        # Schema might already exist, continue anyway
        print(f"Note: Could not register DICOM schema (may already exist): {e}")

    # Register the Permissions schema
    permissions_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "Permissions",
        "description": "Permissions and project associations for the entity",
        "properties": {
            "project": {
                "type": "string",
                "description": "Project ID that owns this entity",
            },
            "owner": {
                "type": ["string", "null"],
                "description": "Owner of the entity, null by default",
            },
        },
        "additionalProperties": True,
    }

    try:
        response = requests.post(
            f"{data_api_url}/metadata/keys/permissions",
            json=permissions_schema,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        print("Successfully registered Permissions metadata schema")
    except requests.exceptions.RequestException as e:
        print(f"Note: Could not register Permissions schema (may already exist): {e}")

    # Register the Validation Results schema (generic, permissive)
    validation_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "title": "Validation Results",
        "description": "Results produced by validators, potentially including HTML reports",
        "additionalProperties": True,
    }

    try:
        response = requests.post(
            f"{data_api_url}/metadata/keys/dicom-series-validation",
            json=validation_schema,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        print("Successfully registered Validation metadata schema")
    except requests.exceptions.RequestException as e:
        print(f"Note: Could not register Validation schema (may already exist): {e}")

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

        series_uid = metadata.get(DicomTags.series_uid_tag)
        study_uid = metadata.get(DicomTags.study_uid_tag)
        instance_uid = metadata.get(DicomTags.SOPInstanceUID_tag)

        if not series_uid or not study_uid:
            print(
                f"Warning: Missing series UID or study UID in metadata file {metadata_file}"
            )
            continue

        # Generate UUID for entity ID
        entity_id = str(uuid4())

        # Create or update entity with metadata and PACS storage coordinates
        entity_data = {
            "id": entity_id,
            "storage_coordinates": [
                {
                    "type": "pacs",
                    "pacs_id": f"http://dicom-web-filter-service.{kaapana_settings.services_namespace}.svc:8080",
                    "study_uid": study_uid,
                    "series_uid": series_uid,
                    "instance_uid": instance_uid,
                }
            ],
            "metadata": [{"key": "dicom-series", "data": metadata, "artifacts": []}],
        }

        try:
            response = requests.post(
                f"{data_api_url}/entities",
                json=entity_data,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            print(
                f"Successfully created/updated entity {entity_id} for series {series_uid}"
            )
        except requests.exceptions.RequestException as e:
            print(f"Error creating entity for series {series_uid}: {e}")
            continue

        # Upload thumbnail as artifact if it exists
        thumbnails = [f for f in thumbnail_dir.glob("*.png")]
        if thumbnails:
            assert len(thumbnails) == 1
            thumbnail_path = thumbnails[0]

            try:
                with open(thumbnail_path, "rb") as thumbnail_file:
                    files = {"file": (thumbnail_path.name, thumbnail_file, "image/png")}
                    response = requests.post(
                        f"{data_api_url}/entities/{entity_id}/metadata/dicom-series/artifacts/thumbnail",
                        files=files,
                    )
                    response.raise_for_status()
                    print(f"Successfully uploaded thumbnail for series {series_uid}")
            except requests.exceptions.RequestException as e:
                print(f"Error uploading thumbnail for series {series_uid}: {e}")

        # Add permissions metadata if project was found
        # Extract project name and fetch project details
        project_name = metadata.get(DicomTags.clinical_trial_protocol_id_tag)
        project = None
        if project_name:
            try:
                response = requests.get(
                    f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects"
                )
                response.raise_for_status()
                projects = response.json()
                matching_projects = [
                    p for p in projects if p.get("name") == project_name
                ]
                if matching_projects:
                    project = matching_projects[0]
                else:
                    print(f"Warning: Project '{project_name}' not found")
            except requests.exceptions.RequestException as e:
                print(f"Warning: Failed to fetch projects: {e}")

        if project:
            permissions_entry = {
                "key": "permissions",
                "data": {"project": project.get("id"), "owner": None},
                "artifacts": [],
            }

            try:
                response = requests.post(
                    f"{data_api_url}/entities/{entity_id}/metadata",
                    json=permissions_entry,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                print(
                    f"Added permissions metadata to entity {entity_id} for project {project.get('id')}"
                )
            except requests.exceptions.RequestException as e:
                print(f"Error adding permissions metadata for entity {entity_id}: {e}")

        # Add validation results
        # Append validation metadata and upload HTML report artifacts
        validator_results_dir = Path(batch_element_dir) / validate.operator_out_dir
        validation_reports = [f for f in validator_results_dir.glob("*.html")]

        if validation_reports:
            # Prefer validator-produced JSON as the metadata payload
            validation_json_files = [f for f in validator_results_dir.glob("*.json")]
            validation_payload = None
            if validation_json_files:
                try:
                    with open(validation_json_files[0], "r") as vf:
                        validation_payload = json.load(vf)
                except Exception as e:
                    print(
                        f"Warning: Failed to load validation JSON '{validation_json_files[0]}': {e}"
                    )

            # Fallback to a minimal payload with report names if JSON is unavailable
            if validation_payload is None:
                validation_payload = {
                    "reports": [report.name for report in validation_reports],
                    "source": "DcmValidatorOperator",
                }

            validation_entry = {
                "key": "dicom-series-validation",
                "data": validation_payload,
                "artifacts": [],
            }

            try:
                response = requests.post(
                    f"{data_api_url}/entities/{entity_id}/metadata",
                    json=validation_entry,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                print(f"Added validation metadata to entity {entity_id}")

                # Upload each HTML report as an artifact under the 'validation' metadata
                for report_path in validation_reports:
                    artifact_id = f"report-{report_path.stem}"
                    try:
                        with open(report_path, "rb") as report_file:
                            files = {
                                "file": (
                                    report_path.name,
                                    report_file,
                                    "text/html",
                                )
                            }
                            response = requests.post(
                                f"{data_api_url}/entities/{entity_id}/metadata/dicom-series-validation/artifacts/{artifact_id}",
                                files=files,
                            )
                            response.raise_for_status()
                            print(
                                f"Uploaded validation report artifact '{artifact_id}' for entity {entity_id}"
                            )
                    except requests.exceptions.RequestException as e:
                        print(
                            f"Error uploading validation report '{report_path.name}' for entity {entity_id}: {e}"
                        )
            except requests.exceptions.RequestException as e:
                print(f"Error adding validation metadata for entity {entity_id}: {e}")


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

upload_to_data_api = KaapanaPythonBaseOperator(
    name="upload-series-to-data-api",
    python_callable=upload_series_to_data_api,
    dag=dag,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    namespace=SERVICES_NAMESPACE,
)

get_input >> (auto_trigger_operator, extract_metadata)

extract_metadata >> (push_json, add_to_dataset, assign_to_project, remove_tags)


push_json >> (validate, branch_by_has_ref_series)
(
    validate
    >> save_to_meta
    >> (put_html_to_minio, put_results_html_to_minio_admin_bucket, generate_thumbnail)
)
branch_by_has_ref_series >> (get_ref_ct_series, generate_thumbnail)

remove_tags >> dcm_send

(get_ref_ct_series >> generate_thumbnail >> put_thumbnail_to_project_bucket)

generate_thumbnail >> upload_to_data_api
extract_metadata >> upload_to_data_api
validate >> upload_to_data_api

[
    add_to_dataset,
    assign_to_project,
    dcm_send,
    put_html_to_minio,
    put_results_html_to_minio_admin_bucket,
    put_thumbnail_to_project_bucket,
    upload_to_data_api,
] >> clean
