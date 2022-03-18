
import os
from datetime import timedelta
from datetime import datetime


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule


from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet_federated.nnUNetFederatedOperator import nnUNetFederatedOperator


log = LoggingMixin().log

remote_dag_id = "nnunet-training"
ui_forms = {
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            "federated_total_rounds": "$default",
            "remote_dag_id": {
                "type": "string",
                "title": "Remote dag id",
                "default": remote_dag_id,
                "readOnly": True,
                "required": True,
            },
            "federated_operators": {
                "type": "array",
                "title": "Federated operators",
                "items": {
                    "type": 'string',
                    "enum": [
                        "nnunet-training",
                    ],
                },
                "default": ["nnunet-training"],
                "required": True,
                "readOnly": True
            },
            "skip_operators": {
                "type": "array",
                "title": "Skip operators",
                "items": {
                    "type": 'string',
                    "enum": [
                        "zip-unzip-training", "model2dicom", "dcmsend", "upload-nnunet-data", "pdf2dcm-training", "dcmsend-pdf", "generate-nnunet-report-training"
                    ],
                },
                "default": ["zip-unzip-training", "model2dicom", "dcmsend", "upload-nnunet-data", "pdf2dcm-training", "dcmsend-pdf", "generate-nnunet-report-training"],
                "required": True,
                "readOnly": True
            }
        },
    },
    "external_schemas": remote_dag_id
}

args = {
    'ui_visible': False,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='nnunet-federated',
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None
)

nnunet_federated = nnUNetFederatedOperator(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)
nnunet_federated >> clean