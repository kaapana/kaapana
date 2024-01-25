from airflow.utils.dates import days_ago
from airflow.models import DAG
from tfda_spe_orchestrator.LocalTriggerContainerIsolationOperator import (
    LocalTriggerContainerIsolationOperator,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from datetime import timedelta
from kaapana.operators.HelperMinio import HelperMinio

buckets = HelperMinio.minioClient.list_buckets()
bucket_names = [bucket.name for bucket in buckets]

ui_forms = {
    "data_form": {
        "type": "object",
        "properties": {
            "bucket_name": {
                "title": "Select Data to process",
                "description": "It should be the name of a Bucket from MinIO store",
                "type": "string",
                "enum": list(set(bucket_names)),
                "readOnly": False,
            }
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "container_registry_url": {
                "title": "Enter container registry URL",
                "type": "string",
                "required": True
            },
            "container_registry_user": {
                "title": "Enter container registry username (optional)",
                "description": "Enter only if downloading your container needs login",
                "type": "string"
            },
            "container_registry_pwd": {
                "title": "Enter container registry password (optional)",
                "description": "Enter only if downloading your container needs login",
                "type": "string",
                "x-props": {"type": "password"},
                "readOnly": False
            },
            "container_name_version": {
                "title": "Enter container name:version",
                "type": "string",
                "required": True
            },
        },
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(minutes=10),
}

dag = DAG(
    dag_id="isolated-container-workflow",
    default_args=args,
    schedule_interval=None,
)

iso_env_orchestration = LocalTriggerContainerIsolationOperator(
    dag=dag, execution_timeout=timedelta(hours=24)
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

iso_env_orchestration >> clean
