from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.operators.DcmValidatorOperator import DcmValidatorOperator
from kaapana.operators.LocalClearValidationResultOperator import (
    LocalClearValidationResultOperator,
)
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalValidationResult2MetaOperator import (
    LocalValidationResult2MetaOperator,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "validator_algorithm": {
                "title": "Validator Algorithm",
                "description": "Choose the algorithm to validate your dicoms",
                "enum": ["dicom-validator", "dciodvfy"],
                "type": "string",
                "default": "dicom-validator",
                "required": True,
            },
            "exit_on_error": {
                "title": "Stop execution on Validation Error",
                "description": "Validator will raise an error and stop executing on validation fail if set to True",
                "type": "boolean",
                "default": False,
            },
            "tags_whitelist": {
                "type": "array",
                "title": "Tags Whitelist",
                "description": "List of DICOM tags, that will be ignored while validating",
                "items": {"type": "string", "title": "DICOM tag"},
                "default": [],
            },
        },
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

dag = DAG(dag_id="validate-dicoms", default_args=args, schedule_interval=None)


get_input = LocalGetInputDataOperator(dag=dag)

validate = DcmValidatorOperator(
    dag=dag,
    input_operator=get_input,
    exit_on_error=False,
)

get_input_json = LocalGetInputDataOperator(
    dag=dag, name="get-json-input-data", data_type="json"
)

clear_validation_results = LocalClearValidationResultOperator(
    dag=dag,
    name="clear-validation-results",
    input_operator=get_input_json,
    result_bucket="staticwebsiteresults",
)

save_to_meta = LocalValidationResult2MetaOperator(
    dag=dag,
    input_operator=get_input_json,
    validator_output_dir=validate.operator_out_dir,
    validation_tag="00111001",
)

put_html_to_minio = LocalMinioOperator(
    dag=dag,
    action_operator_dirs=[validate.operator_out_dir],
    name="put-results-html-to-minio",
    action="put",
    bucket_name="staticwebsiteresults",
    file_white_tuples=(".html"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    get_input
    >> validate
    >> get_input_json
    >> clear_validation_results
    >> save_to_meta
    >> put_html_to_minio
    >> clean
)
