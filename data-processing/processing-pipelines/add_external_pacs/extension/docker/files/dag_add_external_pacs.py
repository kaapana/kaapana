from datetime import timedelta

from add_external_pacs.InitExternalPacsOperator import InitExternalPacsOperator
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

gcloud = "https://healthcare.googleapis.com/v1"
project_id = "/projects/idc-external-031"
location = "/locations/europe-west2"
dataset_id = "/datasets/kaapana-integration-test"
dicom_store_id = "/dicomStores/kaapana-integration-test-store"
ae_title = "external-data"

default_host = (
    gcloud + project_id + location + dataset_id + dicom_store_id + "/dicomWeb"
)
ui_forms = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "dcmweb_endpoint": {
                "title": "Pacs host",
                "description": "Specify the url/IP of the DICOM receiver.\n"
                "gcloud: https://healthcare.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/datasets/DATASET_ID/dicomStores?dicomStoreId=DICOM_STORE_ID\n",
                "type": "string",
                "default": default_host,
                "required": True,
            },
            "ae_title": {
                "title": "Dataset Name",
                "description": "Name of the dataset appearing in the Kaapana",
                "type": "string",
                "default": ae_title,
                "required": True,
            },
            "service_account_info": {
                "title": "service_account_info json",
                "description": "Content of the credentials file, such as credentials.json for Google Cloud. Beware! It WILL BE stored in platform in order to not ask you again.",
                "type": "string",
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
    dag_id="add-external-pacs",
    default_args=args,
    concurrency=50,
    max_active_runs=20,
    schedule_interval=None,
)

init_operator = InitExternalPacsOperator(dag=dag)
get_input = LocalGetInputDataOperator(dag=dag)
extract_metadata = LocalDcm2JsonOperator(
    dag=dag, input_operator=get_input, data_type="json"
)
add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)

push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=get_input, json_operator=extract_metadata
)
tagging = LocalTaggingOperator(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    init_operator
    >> get_input
    >> extract_metadata
    >> add_to_dataset
    >> push_json
    >> tagging
    >> clean
)  # type: ignore
