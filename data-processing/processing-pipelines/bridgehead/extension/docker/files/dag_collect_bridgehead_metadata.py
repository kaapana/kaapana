from kaapana.operators.MinioOperator import MinioOperator
from bridgehead.LocalBridgeheadOperator import LocalBridgeheadOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

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
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="bridgehead",
    default_args=args,
    concurrency=50,
    max_active_runs=50,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, data_type='json')

bridgehead =LocalBridgeheadOperator(dag=dag, input_operator=get_input)

put_to_minio = MinioOperator(
    dag=dag,
    none_batch_input_operators=[bridgehead],
    action="put",
    minio_prefix="downloads",
    zip_files=True,
)


#clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> bridgehead >> put_to_minio #>> clean
