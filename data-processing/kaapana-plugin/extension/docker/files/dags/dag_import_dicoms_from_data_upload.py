from datetime import timedelta

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalVolumeMountOperator import LocalVolumeMountOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.blueprints.json_schema_templates import schema_upload_form
from kaapana.blueprints.kaapana_global_variables import UPLOAD_PORTAL_AE_TITLE, UPLOAD_PORTAL_PACS, UPLOAD_PORTAL_PORT

log = LoggingMixin().log


ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#import-dicoms-from-data-upload",
    },
    **schema_upload_form(whitelisted_file_formats=(".zip",)),
    "workflow_form": {
        "type": "object",
        "properties": {
            "aetitle": {
                "title": "Dataset name",
                "description": "Specify a name for your dataset.",
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
    dag_id="import-dicoms-from-data-upload",
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
    operator_out_dir="dicoms",
)

unzip_files = ZipUnzipOperator(
    dag=dag, input_operator=get_object_from_uploads, batch_level=True, mode="unzip"
)
#TODO set receiver AE Title, host, port 
dicom_send = DcmSendOperator(dag=dag, ae_title=UPLOAD_PORTAL_AE_TITLE, pacs_host=UPLOAD_PORTAL_PACS, pacs_port=UPLOAD_PORTAL_PORT, input_operator=unzip_files, level="batch", enable_proxy=True,
    no_proxy=".svc,.svc.cluster,.svc.cluster.local",
    labels={"network-access-external-ips": "true"},)

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


get_object_from_uploads >> unzip_files >> dicom_send >> remove_object_from_file_uploads >> clean
