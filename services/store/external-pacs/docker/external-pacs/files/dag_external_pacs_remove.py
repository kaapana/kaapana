from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from external_pacs.ExternalPacsOperator import ExternalPacsOperator

ui_forms = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "dcmweb_endpoint": {
                "title": "DcmWeb URL",
                "description": "Specify the URL of the DICOM store. (e.g.: https://healthcare.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/datasets/DATASET_ID/dicomStores?dicomStoreId=DICOM_STORE_ID)",
                "type": "string",
                "default": None,
                "required": True,
            },
        },
    },
}


args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="external-pacs-remove",
    default_args=args,
    max_active_runs=1,
    schedule_interval=None,
)
external_pacs_operator = ExternalPacsOperator(
    dag=dag, action="remove", operator_out_dir="get-input-data"
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(external_pacs_operator >> clean)
