from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from create_classification_dataset.CreateRawDatasetOperator import CreateRawDatasetOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "tag_to_class_mapping_json": {
                "title": "Tag to class mapping json",
                "description": 'Specify the respective classes of the tags in json format. E.g.: {"tag0": 0, "tag1": 1}',
                "default": '{"CT": 0, "MR": 1}',
                "type": "string",
                "required": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
        },
    }
}

log = LoggingMixin().log

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='create-classification-dataset',
    default_args=args,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input)
create_raw_dataset = CreateRawDatasetOperator(dag=dag, input_operator=convert,
                                # dev_server='code-server'
                                )
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> create_raw_dataset >> clean
