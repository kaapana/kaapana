from datetime import timedelta

from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago


from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.MinioOperator import MinioOperator
from advanced_collect_metadata_federated.AdvancedCollectMetadataFederatedOperator import (
    AdvancedCollectMetadataFederatedOperator,
)

log = LoggingMixin().log

# FL related
# name of DAG which should be executed in a federated way
remote_dag_id = "advanced-collect-metadata"
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

acmd_federated = AdvancedCollectMetadataFederatedOperator(
    dag=dag,
    image_pull_policy="Always",
)

put_to_minio = MinioOperator(
    dag=dag,
    action="put",
    none_batch_input_operators=[acmd_federated],
    minio_prefix="downloads",
    zip_files=True,
    whitelisted_file_extensions=(".json", ".tar"),
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
)


acmd_federated >> put_to_minio >> clean
