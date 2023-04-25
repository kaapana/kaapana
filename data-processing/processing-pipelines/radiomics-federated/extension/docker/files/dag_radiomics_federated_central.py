import os
from datetime import timedelta
from datetime import datetime


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from radiomics_federated.LocalRadiomicsFederatedOperator import LocalRadiomicsFederatedOperator
from radiomics_federated.RadiomicsReportingOperator import RadiomicsReportingOperator

log = LoggingMixin().log

remote_dag_id = "radiomics-federated-node"
skip_operators= ["workflow-cleaner"]
federated_operators = ["radiomics-packaging-operator"]
ui_forms = {
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            "federated_total_rounds": {
                "type": "integer",
                #"title": "Rounds",
                "default": 1,
                "readOnly": True,
                "required": True,
            },
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
                    "enum": federated_operators,
                },
                "default": federated_operators,
                "required": True,
                "readOnly": True
            },
            "skip_operators": {
                "type": "array",
                "title": "Skip operators",
                "items": {
                    "type": 'string',
                    "enum": skip_operators,
                },
                "default": skip_operators,
                "required": True,
                "readOnly": True
            }
        },
    },
    "external_schemas": remote_dag_id
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='radiomics-federated-central',
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None
)

radiomics_federated_central = LocalRadiomicsFederatedOperator(dag=dag)
put_radiomics_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[radiomics_federated_central])
radiomics_reporting = RadiomicsReportingOperator(dag=dag, input_operator=radiomics_federated_central)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

radiomics_federated_central >> put_radiomics_to_minio >> clean
radiomics_federated_central >> radiomics_reporting >> clean