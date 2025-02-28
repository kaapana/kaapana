from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.MinioOperator import MinioOperator


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
            }
        },
    }
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(dag_id="example-dcm2nrrd", default_args=args, schedule_interval=None)


get_input = GetInputOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input, output_format="nrrd")
put_to_minio = MinioOperator(
    dag=dag, action="put", batch_input_operators=[convert], whitelisted_file_extensions=(".nrrd")
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> put_to_minio >> clean
