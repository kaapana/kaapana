from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "action": {
                "title": "Action",
                "description": "Choose if you want to add/delete tags",
                "enum": ["add", "delete"],
                "type": "string",
                "default": "add",
                "required": True
            },
            "tags": {
                "title": "Tags",
                "description": "Specify a , seperated list of tags to add/delete (e.g. tag1,tag2)",
                "type": "string",
                "default": "",
                "required": True
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_federated': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='tag-dataset',
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, data_type="json")
tagging = LocalTaggingOperator(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> tagging >> clean
