import glob
import json
import os
import shutil
from datetime import timedelta
from pathlib import Path

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.blueprints.json_schema_templates import get_all_projects
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DeleteFromMetaOperator import DeleteFromMetaOperator
from kaapana.operators.DeleteFromPacsOperator import DeleteFromPacsOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.KaapanaBranchPythonBaseOperator import (
    KaapanaBranchPythonBaseOperator,
    KaapanaPythonBaseOperator,
)
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalAssignDataToProjectOperator import (
    LocalAssignDataToProjectOperator,
)
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log
import requests

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "projects": {
                "title": "Destination Projects",
                "description": "The project(s) to which the data will be copied.",
                "type": "array",
                "items": {"type": "string", "enum": get_all_projects()},
                "required": True,
            },
            "copy_dataset": {
                "title": "Copy Dataset Name",
                "type": "boolean",
                "description": "If a dataset is selected, should its name also be copied to the destination project?",
                "default": True,
            },
            "keep_tags": {
                "title": "Keep Tags",
                "type": "boolean",
                "description": "Should tags also be copied?",
                "default": True,
            },
            "single_execution": {
                "title": "Process Series Separately",
                "description": "Should each series be processed individually?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="project-dicom-transfer",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)


class LocalCleanCustomTagsOperator(KaapanaPythonBaseOperator):
    def clean(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        log.info(f"{conf=}")
        keep_tags = bool(conf["workflow_form"]["keep_tags"])
        log.info(f"{keep_tags=}")
        batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
        batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
        for batch_element_dir in batch_folder:
            # Find all JSON files in the input directory
            json_files = sorted(
                list(Path(batch_element_dir, self.operator_in_dir).rglob("*.json"))
            )

            # Create output directory if it doesn't exist
            out_dir = os.path.join(batch_element_dir, self.operator_out_dir)
            os.makedirs(out_dir, exist_ok=True)

            if keep_tags:
                # Simply copy all JSON files to output directory
                for json_file in json_files:
                    dest_path = os.path.join(out_dir, os.path.basename(json_file))
                    shutil.copy(json_file, dest_path)
            else:
                # Process each file to remove tags
                for json_file in json_files:
                    with open(json_file) as fs:
                        metadata = json.load(fs)
                        # Remove tags if they exist
                        if "00000000 Tags_keyword" in metadata:
                            metadata.pop("00000000 Tags_keyword")

                    # Save modified metadata to output directory
                    dest_path = os.path.join(out_dir, os.path.basename(json_file))
                    with open(dest_path, "w") as fp:
                        json.dump(metadata, fp, indent=4, sort_keys=True)

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag, name="clean-custom-dags", python_callable=self.clean, **kwargs
        )


class LocalCopyThumbnails(KaapanaPythonBaseOperator):
    def copy_thumbnails(self, ds, **kwargs):
        from kaapanapy.helper import get_minio_client
        from kaapanapy.settings import KaapanaSettings
        from minio.commonconfig import CopySource
        from minio.error import S3Error

        kaapana_settings = KaapanaSettings()
        minio = get_minio_client()

        batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
        batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
        for batch_element_dir in batch_folder:
            json_files = sorted(
                list(Path(batch_element_dir, self.operator_in_dir).rglob("*.json"))
            )
            assert len(json_files) == 1
            metadata_file = json_files[0]
            with open(metadata_file, "r") as f:
                metadata = json.load(f)

            series_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
            minio_object_path = f"thumbnails/{series_uid}.png"

            # get thumbnail from admin project:
            # Get source project info
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            source_project = response.json()
            source_bucket = source_project.get("s3_bucket")

            # Get form data and target projects
            workflow_form = kwargs["dag_run"].conf.get("workflow_form")
            projects = workflow_form.get("projects")

            # Copy to each target project
            for project_name in projects:
                response = requests.get(
                    f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/{project_name}"
                )
                target_project = response.json()
                target_bucket = target_project.get("s3_bucket")

                # Direct copy between buckets with exception handling
                try:
                    # Create a CopySource object for the source
                    source = CopySource(source_bucket, minio_object_path)

                    # Perform the copy operation
                    minio.copy_object(
                        bucket_name=target_bucket,
                        object_name=minio_object_path,
                        source=source,
                    )
                    log.info(
                        f"Copied object '{minio_object_path}' to bucket '{target_bucket}'."
                    )
                except S3Error as err:
                    # Check if the error is because the source file doesn't exist
                    if err.code == "NoSuchKey":
                        log.info(f"Non-existing thumbnail for {series_uid}")
                    else:
                        # Re-raise other S3 errors
                        raise

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag,
            name="copy-thumbnails",
            python_callable=self.copy_thumbnails,
            **kwargs,
        )


get_input = GetInputOperator(dag=dag, data_type="json")
clean_tags = LocalCleanCustomTagsOperator(dag=dag, input_operator=get_input)
## use local operator to push to different projects
assign_to_project = LocalAssignDataToProjectOperator(
    dag=dag, from_other_project=True, input_operator=clean_tags
)
add_datasets = LocalAddToDatasetOperator(
    dag=dag, from_other_project=True, input_operator=clean_tags
)
push_json = LocalJson2MetaOperator(
    dag=dag, json_operator=clean_tags, from_other_project=True
)
copy_thumbnails = LocalCopyThumbnails(dag=dag, input_operator=clean_tags)


clean = LocalWorkflowCleanerOperator(
    dag=dag, clean_workflow_dir=True, trigger_rule="none_failed_or_skipped"
)

(
    get_input
    >> clean_tags
    >> assign_to_project
    >> push_json
    >> add_datasets
    >> copy_thumbnails
    >> clean
)
