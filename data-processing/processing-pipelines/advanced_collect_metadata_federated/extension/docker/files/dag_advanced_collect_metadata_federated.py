import os
from datetime import timedelta
from datetime import datetime


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from kaapana.blueprints.json_schema_templates import properties_external_federated_form
from kaapana.blueprints.kaapana_global_variables import (
    INSTANCE_NAME,
    SERVICES_NAMESPACE,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from advanced_collect_metadata_federated.AdvancedCollectMetatdataFederatedOperator import (
    AdvancedCollectMetatdataFederatedOperator,
)

log = LoggingMixin().log

# FL related
# name of DAG which should be executed in a federated way
remote_dag_id = "advanced-collect-metadata"

# skip_operators are operators which are skipped during a round of the remote_dag
skip_operators = []

# federated_operators are operators which are executed during a round of the remote_dag
federated_operators = ["merge_branches"]

# UI forms
ui_forms = {
    "data_form": {},
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            "federated_total_rounds": {
                "type": "integer",
                # "title": "Rounds",
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
    "ui_visible": True,  # DAG cannot be selected in Meta-Dashboard
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="advanced-collect-metadata-federated",
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None,
)

acmd_federated = AdvancedCollectMetatdataFederatedOperator(
    dag=dag,
    # dev_server="code-server",
    image_pull_policy="Always",
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    action="put",
    action_operators=[acmd_federated],
    zip_files=True,
    file_white_tuples=(".zip"),
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
)


acmd_federated >> put_to_minio >> clean
