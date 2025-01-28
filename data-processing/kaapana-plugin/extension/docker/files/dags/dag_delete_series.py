import glob
import os
from datetime import timedelta
from pathlib import Path

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DeleteFromMetaOperator import DeleteFromMetaOperator
from kaapana.operators.DeleteFromPacsOperator import DeleteFromPacsOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapanapy.helper.HelperOpensearch import DicomTags

log = LoggingMixin().log
ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#delete-series",
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "delete_complete_study": {
                "title": "Delete entire study",
                "default": False,
                "type": "boolean",
                "readOnly": False,
            },
        },
    },
}


args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=15),
}

dag = DAG(
    dag_id="delete-series",
    default_args=args,
    concurrency=30,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type="json")


def set_skip_if_dcm_is_external(ds, **kwargs):
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]

    for batch_element_dir in batch_folder:
        input_dir = Path(batch_element_dir) / get_input.operator_out_dir
        json_files = sorted(
            glob.glob(
                os.path.join(input_dir, "*.json*"),
                recursive=True,
            )
        )
        for json_file in json_files:
            with open(json_file, "r") as f:
                metadata = json.load(f)
            if (
                metadata.get("00020016 SourceApplicationEntityTitle")
                == "kaapana_external"
            ):
                raise AirflowSkipException("DICOM file is comes from external PACS")
    return


skip_if_dcm_is_external = KaapanaPythonBaseOperator(
    name="skip_if_dcm_is_external",
    pool="default_pool",
    pool_slots=1,
    python_callable=set_skip_if_dcm_is_external,
    dag=dag,
)


delete_dcm_pacs = DeleteFromPacsOperator(
    dag=dag, input_operator=get_input, delete_complete_study=False, retries=1
)
delete_dcm_meta = DeleteFromMetaOperator(
    dag=dag, input_operator=get_input, delete_complete_study=False, retries=1
)


def remove_thumbnail_from_project_bucket(ds, **kwargs):
    """
    Remove the generated thumbnail from the project bucket,
    where project is determined from the "00120020 ClinicalTrialProtocolID_keyword" tag of the dicom metadata.
    Additionally uploads the thumbnails to the project bucket of the admin project.
    """
    import json

    import requests
    from kaapanapy.helper import get_minio_client
    from kaapanapy.settings import KaapanaSettings

    kaapana_settings = KaapanaSettings()
    minio = get_minio_client()

    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / get_input.operator_out_dir
        json_files = [f for f in json_dir.glob("*.json")]

        assert len(json_files) == 1
        metadata_file = json_files[0]
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        project_name = metadata.get(DicomTags.clinical_trial_protocol_id_tag)
        response = requests.get(
            f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/{project_name}"
        )
        project = response.json()
        series_uid = metadata.get(DicomTags.series_uid_tag)
        minio_object_path = f"thumbnails/{series_uid}.png"
        minio.remove_object(
            bucket_name=project.get("s3_bucket"),
            object_name=minio_object_path,
        )

        if project_name != "admin":
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            project = response.json()
            minio.remove_object(
                bucket_name=project.get("s3_bucket"),
                object_name=minio_object_path,
            )


remove_thumbnail_from_project_bucket = KaapanaPythonBaseOperator(
    name="remove_thumbnail_from_project_bucket",
    python_callable=remove_thumbnail_from_project_bucket,
    dag=dag,
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    get_input
    >> delete_dcm_pacs
    >> delete_dcm_meta
    >> remove_thumbnail_from_project_bucket
    >> clean
)
