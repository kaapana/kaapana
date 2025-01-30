from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator

from kaapana.operators.LocalAssignDataToProjectOperator import (
    LocalAssignDataToProjectOperator,
)
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from external_pacs.ExternalPacsOperator import ExternalPacsOperator


dataset_name = "external-data"
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
            "tags": {
                "title": "Tags",
                "description": "Specify a , seperated list of tags to add (e.g. tag1,tag2)",
                "type": "string",
                "default": "external",
                "required": True,
            },
            "dataset_name": {
                "title": "Dataset Name",
                "description": "Name of the dataset appearing in the Kaapana",
                "type": "string",
                "default": dataset_name,
                "required": True,
            },
            "service_account_info": {
                "title": "Service Account Info (credentials.json)",
                "description": "Content of the credentials file, such as credentials.json for Google Cloud. Beware! It WILL BE stored in platform in order to not ask you again.",
                "required": True,
                "type": "string",
                "contentMediaType": "application/json",
                "x-display": "file",
                "writeOnly": True,
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
    dag_id="external-pacs-add",
    default_args=args,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = ExternalPacsOperator(dag=dag, action="add", operator_out_dir="get-input-data")

extract_metadata = LocalDcm2JsonOperator(
    dag=dag, input_operator=get_input, data_type="json"
)
add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)
assign_to_project = LocalAssignDataToProjectOperator(
    dag=dag, input_operator=extract_metadata
)
push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=get_input, json_operator=extract_metadata
)
tagging = LocalTaggingOperator(dag=dag, input_operator=get_input)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)

(get_input >> extract_metadata >> add_to_dataset >> push_json >> tagging >> clean)
