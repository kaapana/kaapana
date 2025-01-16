from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.DeleteFromMetaOperator import DeleteFromMetaOperator
from kaapana.operators.DeleteFromPacsOperator import DeleteFromPacsOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log
ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "delete_complete_study": {
                "title": "Delete entire study",
                "default": False,
                "type": "boolean",
                "readOnly": False,
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
    "retry_delay": timedelta(seconds=15),
}

dag = DAG(
    dag_id="delete-series-from-platform",
    default_args=args,
    concurrency=30,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type="json")
delete_dcm_pacs = DeleteFromPacsOperator(
    dag=dag, input_operator=get_input, delete_complete_study=False, retries=1
)
delete_dcm_meta = DeleteFromMetaOperator(
    dag=dag, input_operator=get_input, delete_complete_study=False, retries=1
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> delete_dcm_pacs >> delete_dcm_meta >> clean
