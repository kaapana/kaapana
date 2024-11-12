from datetime import timedelta
from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from kaapana.blueprints.json_schema_templates import properties_external_federated_form
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet_federated.nnUNetFederatedOperator import nnUNetFederatedOperator
from nnunet.InstallNnunetModelOperator import InstallNnunetModelOperator

log = LoggingMixin().log
## nnUnet related
study_id = "KaapanaFederated"
dicom_model_slice_size_limit = 70
training_results_study_uid = None
ae_title = "nnU-Net-results"

## FL releated
remote_dag_id = "nnunet-training"
skip_operators = [
    "nnunet-training",
    "install-model-training",
    "workflow-cleaner",
]
federated_operators = ["nnunet-preprocess", "nnunet-training"]

ui_forms = {
    "viewNames": ["federatedExecution"],
    "data_form": {},
    "external_schema_federated_form": {
        "type": "object",
        "properties": {
            **properties_external_federated_form(
                [
                    "federated_total_rounds",
                    "aggregation_strategy",
                ]
            ),
            "remote_dag_id": {
                "type": "string",
                "title": "Remote dag id",
                "default": remote_dag_id,
                "readOnly": True,
                "required": True,
                "x-display": "hidden",
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
                "x-display": "hidden",
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
                "x-display": "hidden",
            },
            "global_fingerprint": {
                "type": "string",
                "title": "Global fingerprint generation",
                "enum": ["estimate"],
                "description": "accurate: Clients share partially voxel data for accurate fingerprint statistic computation; more accurate, less privacy-preserving, slower!\nestimate: Clients share data fingerprints, server estimates global data fingerprint statistics; less accurate, more privacy-preserving, faster!",
                "default": "estimate",
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
    dag_id="nnunet-federated",
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None,
)

nnunet_federated = nnUNetFederatedOperator(
    dag=dag,
    # dev_server="code-server"
)

install_model = InstallNnunetModelOperator(
    dag=dag,
    operator_in_dir = "nnunet-training",
    overwrite_models=True
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
nnunet_federated >> install_model >> clean
