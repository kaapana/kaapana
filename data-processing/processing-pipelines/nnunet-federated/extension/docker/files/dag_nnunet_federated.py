
import os
from datetime import timedelta
from datetime import datetime


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from kaapana.blueprints.json_schema_templates import properties_external_federated_form
from kaapana.blueprints.kaapana_global_variables import INSTANCE_NAME, SERVICES_NAMESPACE
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from nnunet_federated.nnUNetFederatedOperator import nnUNetFederatedOperator


log = LoggingMixin().log
## nnUnet related
study_id = "KaapanaFederated"
dicom_model_slice_size_limit = 70
training_results_study_uid = None
ae_title = "nnUnet-results"

## FL releated
remote_dag_id = "nnunet-training"
# skip_operators = ["zip-unzip-training", "model2dicom", "dcmsend", "upload-nnunet-data", "pdf2dcm-training", "dcmsend-pdf", "generate-nnunet-report-training"]
# federated_operators = ["nnunet-training"]
skip_operators = ["nnunet-training", "zip-unzip-training", "model2dicom", "dcmsend", "generate-nnunet-report-training", "upload-nnunet-data", "upload-staticwebsiteresults", "pdf2dcm-training", "dcmsend-pdf", "workflow-cleaner"]
federated_operators = ["nnunet-preprocess", "nnunet-training"]
ui_forms = {
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
                    "type": 'string',
                    "enum": federated_operators,
                },
                "default": federated_operators,
                "required": True,
                "readOnly": True
            },
            "skip_operators": {
                "type": "array",
                "title": "Skip operators",
                "items": {
                    "type": 'string',
                    "enum": skip_operators,
                },
                "default": skip_operators,
                "required": True,
                "readOnly": True
            }
        },
    },
    "external_schemas": remote_dag_id
}

args = {
    'ui_visible': False,
    'ui_federated': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='nnunet-federated',
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None
)

nnunet_federated = nnUNetFederatedOperator(dag=dag, dev_server=None)

zip_model = ZipUnzipOperator(
    dag=dag,
    target_filename=f"nnunet_model.zip",
    whitelist_files="model_latest.model.pkl,model_latest.model,model_final_checkpoint.model,model_final_checkpoint.model.pkl,plans.pkl,*.json,*.png,*.pdf",
    subdir="results/nnUNet",
    mode="zip",
    batch_level=True,
    operator_in_dir='nnunet-training'
)


bin2dcm = Bin2DcmOperator(
    dag=dag,
    dataset_info_operator_in_dir='nnunet-training',
    name="model2dicom",
    patient_name="nnUNet-model",
    patient_id=INSTANCE_NAME,
    instance_name=INSTANCE_NAME,
    manufacturer="Kaapana",
    manufacturer_model="nnUNet",
    version="03-22",
    study_id=study_id,
    study_uid=training_results_study_uid,
    protocol_name=None,
    study_description=None,
    series_description=f"nnUNet model {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    size_limit=dicom_model_slice_size_limit,
    input_operator=zip_model,
    file_extensions="*.zip"
)

dcm_send_int = DcmSendOperator(
    dag=dag,
    level="batch",
    pacs_host=f'ctp-dicom-service.{SERVICES_NAMESPACE}.svc',
    pacs_port='11112',
    ae_title=ae_title,
    input_operator=bin2dcm
)

put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[nnunet_federated], zip_files=True, file_white_tuples=('.zip'))

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
nnunet_federated >> zip_model >> bin2dcm >> dcm_send_int >> clean
nnunet_federated >> put_to_minio >> clean