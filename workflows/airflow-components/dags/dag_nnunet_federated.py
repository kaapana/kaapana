
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

ui_forms = {
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            "federated_total_rounds": "$default"
        }
    },
    # "workflow_form": {
    #     "type": "object",
    #     "properties": {
    #         "federated_updates": {
    #             "type": "integer",
    #             "title": "Number of total upd"
    #         },
    #     }
    # },
    "external_schemas": "nnunet-training"
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