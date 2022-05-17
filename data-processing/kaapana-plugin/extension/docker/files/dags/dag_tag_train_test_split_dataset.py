from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.TrainTestSplitOperator import TrainTestSplitOperator

from airflow.utils.dates import days_ago
from airflow.models import DAG


ui_forms = {
    "elasticsearch_form": {
        "type": "object",
        "properties": {
            "dataset": "$default",
            "index": "$default",
            "cohort_limit": "$default",
            "input_modality": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
                "required": True
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "train_aetitle": {
                "title": "Train dataset name",
                "description": "Name of the train dataset.",
                "type": "string",
                "required": True
            },
            "test_aetitle": {
                "title": "Test dataset name",
                "description": "Name of the test dataset",
                "type": "string",
                "required": True
            },
            "split": {
                "title": "Train split",
                "description": "Either an integer indication the number of training samples or floating number between 0 and 1 indication the fraction of training samples",
                "type": "string",
                "required": True
            },
            "random_seed": {
                "title": "Random seed",
                "description": "Random seed",
                "type": "string",
                "default": "1" ,
                "required": False
            }
        }
    }
}

args = {
    'ui_visible': False,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='tag-train-test-split-dataset',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
train_test_split = TrainTestSplitOperator(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> train_test_split >> clean
