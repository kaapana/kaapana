from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from external_pacs.HelperDcmWebEndpointsManager import HelperDcmWebEndpointsManager
from external_pacs.LocalExternalPacsOperator import LocalExternalPacsOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

external_endpoints = HelperDcmWebEndpointsManager().get_endpoints()

ui_form = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "dcmweb_endpoint": {
                "title": "External dicomWeb endpoint",
                "description": "Choose which dicomWeb endpoint to remove",
                "type": "string",
                "enum": list(set(external_endpoints)),
                "required": True,
            },
        },
    },
}


args = {
    "ui_visible": True,
    "ui_forms": ui_form,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="external-pacs-delete",
    default_args=args,
    max_active_runs=1,
    schedule_interval=None,
)
init_operator = LocalExternalPacsOperator(dag=dag, action="delete")
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(init_operator >> clean)  # type: ignore
