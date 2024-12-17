from datetime import timedelta


from airflow.models import DAG
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago

from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.JupyterlabReportingOperator import JupyterlabReportingOperator

from radiomics_federated.RadiomicsFederatedOperator import RadiomicsFederatedOperator

log = LoggingMixin().log

remote_dag_id = "radiomics-dcmseg"
skip_operators = ["workflow-cleaner"]
federated_operators = ["radiomics"]
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
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="radiomics-federated-central",
    default_args=args,
    concurrency=5,
    max_active_runs=1,
    schedule_interval=None,
)

radiomics_federated_central = RadiomicsFederatedOperator(dag=dag)

put_radiomics_to_minio = MinioOperator(
    dag=dag, action="put", none_batch_input_operators=[radiomics_federated_central]
)

get_notebook_from_minio = MinioOperator(
    dag=dag,
    name="radiomics-get-notebook-from-minio",
    bucket_name="template-analysis-scripts",
    action="get",
    source_files=["FedRad-Analysis.ipynb"],
)

radiomics_reporting = JupyterlabReportingOperator(
    dag=dag,
    input_operator=radiomics_federated_central,
    notebook_filename="FedRad-Analysis.ipynb",
    notebook_dir=get_notebook_from_minio.operator_out_dir,
)

put_report_to_minio = MinioOperator(
    dag=dag,
    name="upload-staticwebsiteresults",
    minio_prefix="staticwebsiteresults",
    action="put",
    none_batch_input_operators=[radiomics_reporting],
    whitelisted_file_extensions=(".html", ".pdf"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

radiomics_federated_central >> put_radiomics_to_minio >> clean
(
    radiomics_federated_central
    >> get_notebook_from_minio
    >> radiomics_reporting
    >> put_report_to_minio
    >> clean
)
