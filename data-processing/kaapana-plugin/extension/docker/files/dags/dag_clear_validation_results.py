from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.DcmValidatorOperator import DcmValidatorOperator
from kaapana.operators.LocalValidationResult2MetaOperator import (
    LocalValidationResult2MetaOperator,
)
from kaapana.operators.LocalClearValidationResultOperator import (
    LocalClearValidationResultOperator,
)


ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {},
    }
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

get_input_json = LocalGetInputDataOperator(
    dag=dag, name="get-json-input-data", data_type="json"
)

clear_validation_results = LocalClearValidationResultOperator(
    dag=dag,
    name="clear-validation-results",
    input_operator=get_input_json,
    result_bucket="staticwebsiteresults",
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(get_input_json >> clear_validation_results >> clean)
