from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from external_pacs.LocalExternalPacsOperator import LocalExternalPacsOperator
from external_pacs.LocalExternalThumbnailOperator import LocalExternalThumbnailOperator
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

gcloud = "https://healthcare.googleapis.com/v1"
project_id = "/projects/idc-external-031"
location = "/locations/europe-west2"
dataset_id = "/datasets/kaapana-integration-test"
dicom_store_id = "/dicomStores/kaapana-integration-test-store"
ae_title = "external-data"

default_host = gcloud + project_id + location + dataset_id + dicom_store_id
ui_forms = {
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "dcmweb_endpoint": {
                "title": "DcmWeb URL",
                "description": "Specify the URL of the DICOM store. (e.g.: https://healthcare.googleapis.com/v1/projects/PROJECT_ID/locations/LOCATION/datasets/DATASET_ID/dicomStores?dicomStoreId=DICOM_STORE_ID)",
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

init_operator = LocalExternalPacsOperator(
    dag=dag, operator_out_dir="get-input-data", action="add"
)
extract_metadata = LocalDcm2JsonOperator(
    dag=dag, input_operator=init_operator, data_type="json"
)
add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)

push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=init_operator, json_operator=extract_metadata
)
external_thumbnail = LocalExternalThumbnailOperator(
    dag=dag,
    input_operator=extract_metadata,
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-thumbnail",
    zip_files=False,
    action="put",
    bucket_name="thumbnails",
    action_operators=[external_thumbnail],
    file_white_tuples=(".png"),
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    init_operator
    >> extract_metadata
    >> add_to_dataset
    >> push_json
    >> external_thumbnail
    >> put_to_minio
    >> clean
)  # type: ignore
