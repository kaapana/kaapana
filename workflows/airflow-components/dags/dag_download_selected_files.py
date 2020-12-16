from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator


log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "zip_files": {
                "title": "Do you want to zip the downloaded files?",
                "type": "boolean",
                "default": True,
            },
            "single_execution": {
                "title": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='download-selected-files',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operator_dirs=[get_input.operator_out_dir], bucket_name="downloads", file_white_tuples=('.zip', '.dcm'), zip_files=True)
clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> put_to_minio >> clean
