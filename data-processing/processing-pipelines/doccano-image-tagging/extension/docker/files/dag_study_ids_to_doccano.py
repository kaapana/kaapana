from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from doccano.LocalDoccanoUploadDatasetOperator import LocalDoccanoUploadDatasetOperator
from doccano.LocalCreateStudyIDJsonOperator import LocalCreateStudyIDJsonOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "name": {
                "title": "Name",
                "description": "Give your project a name for doccano.",
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "description": {
                "title": "Description",
                "description": "Give some infos about your project.",
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "project_type": {
                "title": "Project type",
                "default": "DocumentClassification",
                "description": "Choose a project type",
                "enum": ["DocumentClassification", "Seq2seq"],
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
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
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(dag_id="study-ids-to-doccano", default_args=args, schedule_interval=None)


get_input = GetInputOperator(
    dag=dag, operator_out_dir="get-input-data", data_type="json"
)
create_doccano_json = LocalCreateStudyIDJsonOperator(dag=dag, input_operator=get_input)
doccano_upload = LocalDoccanoUploadDatasetOperator(
    dag=dag, input_operator=create_doccano_json
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> create_doccano_json >> doccano_upload >> clean
