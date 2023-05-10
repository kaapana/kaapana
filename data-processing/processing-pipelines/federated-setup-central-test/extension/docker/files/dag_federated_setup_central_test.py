import os
from datetime import timedelta
from datetime import datetime


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from kaapana.blueprints.json_schema_templates import properties_external_federated_form
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from federated_setup_central_test.FedartedSetupCentralTestOperator import (
    FedartedSetupCentralTestOperator,
)

log = LoggingMixin().log

remote_dag_id = "federated-setup-node-test"
skip_operators = ["federated-setup-skip-test", "workflow-cleaner"]
federated_operators = ["federated-setup-federated-test"]
ui_forms = {
    "data_form": {},
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            **properties_external_federated_form(["federated_total_rounds"]),
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
                    "type": "string",
                    "enum": federated_operators,
                },
                "default": federated_operators,
                "required": True,
                "readOnly": True,
            },
            "skip_operators": {
                "type": "array",
                "title": "Skip operators",
                "items": {
                    "type": "string",
                    "enum": skip_operators,
                },
                "default": skip_operators,
                "required": True,
                "readOnly": True,
            },
        },
    },
    "external_schemas": remote_dag_id,
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="federated-setup-central-test",
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None,
)

federated_setup_central_test = FedartedSetupCentralTestOperator(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
federated_setup_central_test >> clean
