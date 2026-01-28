from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#tag-dataset",
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "action": {
                "title": "Action",
                "description": "Choose if you want to add/delete tags",
                "enum": ["add", "delete"],
                "type": "string",
                "default": "add",
                "required": True,
            },
            "tags": {
                "title": "Tags",
                "description": "Specify a , seperated list of tags to add/delete (e.g. tag1,tag2)",
                "type": "string",
                "default": "",
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
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="tag-dataset",
    default_args=args,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type="json")
tagging = LocalTaggingOperator(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> tagging >> clean
