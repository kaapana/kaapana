from datetime import timedelta

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalVolumeMountOperator import LocalVolumeMountOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.blueprints.json_schema_templates import schema_upload_form


log = LoggingMixin().log


ui_forms = {
    **schema_upload_form(whitelisted_file_endings=(".zip",)),
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
    dag_id="import-dicoms-in-zip-to-internal-pacs",
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5,
    tags= ["import"]
)

get_object_from_mount = LocalVolumeMountOperator(
    dag=dag,
    mount_path="/kaapana/app/uploads",
    action="get",
    keep_directory_structure=False,
    name="get-uploads",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
    operator_out_dir="dicoms",
)

unzip_files = ZipUnzipOperator(
    dag=dag, input_operator=get_object_from_mount, batch_level=True, mode="unzip"
)

dicom_send = DcmSendOperator(
    dag=dag, input_operator=unzip_files, ae_title="uploaded", level="batch"
)

remove_object_from_file_mount = LocalVolumeMountOperator(
    dag=dag,
    name="remove-file-from-volume-mount",
    mount_path="/kaapana/app/uploads",
    action="remove",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=True
)


def branching_cleaning_mount_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_file_mount.name]
    else:
        return [clean.name]


branching_cleaning_mount = BranchPythonOperator(
    task_id="branching-cleaning-mount",
    provide_context=True,
    python_callable=branching_cleaning_mount_callable,
    dag=dag,
)

get_object_from_mount >> unzip_files >> dicom_send >> branching_cleaning_mount
branching_cleaning_mount >> remove_object_from_file_mount >> clean
branching_cleaning_mount >> clean
