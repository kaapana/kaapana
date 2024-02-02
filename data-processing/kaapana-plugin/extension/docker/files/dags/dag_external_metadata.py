from kaapana.operators.LocalMetaFromGcloudOperator import LocalMetaFromGcloudOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

project_id = "idc-external-031"
location = "europe-west2"
dataset_id = "kaapana-integration-test"
dicom_store_id = "kaapana-integration-test-store"
ae_title = "external-data"

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "project_id": {
                "title": "Project ID",
                "description": "Specify the ID of the Google Cloud project.",
                "type": "string",
                "default": project_id,
                "required": True,
            },
            "location": {
                "title": "Location",
                "description": "Specify the location of the Google cloud project.",
                "type": "string",
                "default": location,
                "required": True,
            },
            "dataset_id": {
                "title": "Dataset ID",
                "description": "Specify the Dataset ID inside of the specified Google Cloud project.",
                "type": "string",
                "default": dataset_id,
                "required": True,
            },
            "dicom_store_id": {
                "title": "Dicom Store ID",
                "description": "Specify the DicomStoreID inside of the specified Dataset inside of the specified Google Cloud project.",
                "type": "string",
                "default": dicom_store_id,
                "required": True,
            },
            "ae_title": {
                "title": "Dataset Name",
                "description": "Name of the dataset appearing in the Kaapana",
                "type": "string",
                "default": ae_title,
                "required": True,
            },
        },
    }
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
    dag_id="external-metadata",
    default_args=args,
    concurrency=50,
    max_active_runs=20,
    schedule_interval=None,
)

extract_metadata = LocalMetaFromGcloudOperator(
    dag=dag,
    project_id=project_id,
    location=location,
    dataset_id=dataset_id,
    dicom_store_id=dicom_store_id,
    ae_title=ae_title,
)
add_to_dataset = LocalAddToDatasetOperator(
    dag=dag, input_operator=extract_metadata)
push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=extract_metadata, json_operator=extract_metadata)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

extract_metadata >> add_to_dataset >> push_json >> clean
