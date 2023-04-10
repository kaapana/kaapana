from datetime import timedelta

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.blueprints.json_schema_templates import schema_minio_form


log = LoggingMixin().log

ui_forms = {
    **schema_minio_form(whitelist_object_endings = (".zip")),
    "workflow_form": {
        "type": "object",
        "properties": {
            "aetitle": {
                "title": "Dataset tag",
                "description": "Specify a tag for your dataset.",
                "type": "string",
                "default": "dicomupload",
                "required": True
            },
            "dicom_glob_file_extension": {
                "title": "File ending of DICOM files",
                "description": "Most of the times *.dcm in case your DICOMS have no extensions you can try *",
                "type": "string",
                "default": "*.dcm",
                "required": True
            },
            "delete_original_file": {
                "title": "Delete file from Minio after successful upload?",
                "type": "boolean",
                "default": True,
            }
        }
    }
}

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='dicom-upload',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
)

get_object_from_minio = LocalMinioOperator(
    dag=dag,
    local_root_dir="{run_dir}/dicoms",
    action_operator_dirs=["itk"],
    file_white_tuples=('.zip'),
    operator_out_dir='dicoms'
)

unzip_files = ZipUnzipOperator(
    dag=dag,
    input_operator=get_object_from_minio,
    batch_level=True,
    mode="unzip"
)

dicom_send = DcmSendOperator(
    dag=dag,
    input_operator=unzip_files,
    ae_title='uploaded',
    level='batch'
)

remove_object_from_minio = LocalMinioOperator(
    dag=dag,
    action='remove',
    file_white_tuples=('.zip')
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    trigger_rule="none_failed_min_one_success",
    clean_workflow_dir=True
)

def branching_cleaning_minio_callable(**kwargs):
    conf = kwargs['dag_run'].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_minio.name]
    else:
        return [clean.name]

branching_cleaning_minio = BranchPythonOperator(
    task_id='branching-cleaning-minio',
    provide_context=True,
    python_callable=branching_cleaning_minio_callable,
    dag=dag)

get_object_from_minio >> unzip_files >> dicom_send >> branching_cleaning_minio
branching_cleaning_minio >> remove_object_from_minio >> clean
branching_cleaning_minio >> clean