from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.LocalDcmAnonymizerOperator import LocalDcmAnonymizerOperator
from kaapana.operators.LocalConcatJsonOperator import LocalConcatJsonOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

log = LoggingMixin().log

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#collect-metadata",
    },
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
    },
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
    dag_id="collect-metadata",
    default_args=args,
    concurrency=50,
    max_active_runs=50,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag)
anonymizer = LocalDcmAnonymizerOperator(
    dag=dag, input_operator=get_input, single_slice=True
)
extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=anonymizer)
concat_metadata = LocalConcatJsonOperator(
    dag=dag, name="concatenated-metadata", input_operator=extract_metadata
)
put_to_minio = MinioOperator(
    dag=dag,
    action="put",
    none_batch_input_operators=[concat_metadata],
    minio_prefix="downloads",
    zip_files=True,
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> anonymizer >> extract_metadata >> concat_metadata >> put_to_minio >> clean
