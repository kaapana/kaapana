from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.ClearValidationResultOperator import (
    ClearValidationResultOperator,
)
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#clear-validation-results",
    },
    "workflow_form": {
        "type": "object",
        "properties": {},
    },
}

log = LoggingMixin().log

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(dag_id="clear-validation-results", default_args=args, schedule_interval=None)

get_input_json = GetInputOperator(dag=dag, name="get-json-input-data", data_type="json")

clear_validation_results = ClearValidationResultOperator(
    dag=dag,
    name="clear-validation-results",
    input_operator=get_input_json,
    static_results_dir="staticwebsiteresults",
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(get_input_json >> clear_validation_results >> clean)
