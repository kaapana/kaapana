from datetime import timedelta

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from wsiconv.WSIConvOperator import WSIconvOperator
from kaapana.operators.LocalVolumeMountOperator import LocalVolumeMountOperator
from kaapana.blueprints.json_schema_templates import schema_upload_form


log = LoggingMixin().log

ui_forms = {
    **schema_upload_form(whitelisted_file_formats=(".zip",)),
    "workflow_form": {
        "type": "object",
        "properties": {
            "aetitle": {
                "title": "Dataset tag",
                "description": "Specify a tag for your dataset.",
                "type": "string",
                "default": "dicomupload",
                "required": True,
            },
            "delete_original_file": {
                "title": "Delete file from file system after successful upload?",
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
    dag_id="import-WSI",
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5,
)

get_object_from_uploads = LocalVolumeMountOperator(
    dag=dag,
    mount_path="/kaapana/app/uploads",
    action="get",
    keep_directory_structure=False,
    name="get-uploads",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
    operator_out_dir="itk",
)

unzip_files = ZipUnzipOperator(
    dag=dag, input_operator=get_object_from_uploads, batch_level=True, mode="unzip"
)

wsi_conv = WSIconvOperator(
    dag=dag, input_operator=unzip_files
)

dicom_send = DcmSendOperator(
    dag=dag, input_operator=wsi_conv, ae_title="uploaded", level="batch"
)

remove_object_from_uploads = LocalVolumeMountOperator(
    dag=dag, name="removing-object-from-uploads", mount_path="/kaapana/app/uploads", action="remove", whitelisted_file_endings=(".zip",)
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=True
)

def branching_cleaning_uploads_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_uploads.name]
    else:
        return [clean.name]


branching_cleaning_uploads = BranchPythonOperator(
    task_id="branching-cleaning-uploads",
    provide_context=True,
    python_callable=branching_cleaning_uploads_callable,
    dag=dag,
)

get_object_from_uploads >> unzip_files >> wsi_conv >> dicom_send >> branching_cleaning_uploads
branching_cleaning_uploads >> remove_object_from_uploads >> clean
branching_cleaning_uploads >> clean
