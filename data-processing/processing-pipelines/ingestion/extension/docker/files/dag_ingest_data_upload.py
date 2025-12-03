from datetime import timedelta
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from kaapana.blueprints.json_schema_templates import schema_upload_form
from kaapana.operators.LocalVolumeMountOperator import LocalVolumeMountOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from ingestion.LocalIngestionOperator import LocalIngestionOperator

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#import-dicoms-from-data-upload",
    },
    **schema_upload_form(whitelisted_file_formats=(".zip",)),
    "workflow_form": {
        "type": "object",
        "properties": {
            "delete_original_file": {
                "title": "Delete file from file system after successful import?",
                "type": "boolean",
                "default": True,
            },
        },
    },
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="ingest-data-upload",
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5,
    tags=["import"],
)

get_object_from_uploads = LocalVolumeMountOperator(
    dag=dag,
    mount_path="/kaapana/app/uploads",
    action="get",
    keep_directory_structure=False,
    name="get-uploads",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
    operator_out_dir="upload",
)

unzip_files = ZipUnzipOperator(
    dag=dag, input_operator=get_object_from_uploads, batch_level=True, mode="unzip"
)

ingestion = LocalIngestionOperator(dag=dag, input_operator=unzip_files)

remove_object_from_file_uploads = LocalVolumeMountOperator(
    dag=dag,
    name="remove-file-from-volume-uploads",
    mount_path="/kaapana/app/uploads",
    action="remove",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=True
)


def branching_cleaning_uploads_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_file_uploads.name]
    else:
        return [clean.name]


branching_cleaning_uploads = BranchPythonOperator(
    task_id="branching-cleaning-uploads",
    provide_context=True,
    python_callable=branching_cleaning_uploads_callable,
    dag=dag,
)

(
    get_object_from_uploads
    >> unzip_files
    >> ingestion
    >> branching_cleaning_uploads
    >> clean
)
branching_cleaning_uploads >> remove_object_from_file_uploads >> clean
branching_cleaning_uploads >> clean
