from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalTaggingOperator import LocalTaggingOperator
from kaapana.operators.TrainTestSplitOperator import TrainTestSplitOperator

from airflow.utils.dates import days_ago
from airflow.models import DAG


ui_forms = {
    "opensearch_form": {
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
                "required": True
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
            "train_tag": {
                "title": "Train dataset name",
                "description": "Name of the train dataset.",
                "type": "string",
                "required": True
            },
            "test_tag": {
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
    'ui_federated': True,
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
    max_active_runs=1,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, data_type="json")
train_test_split = TrainTestSplitOperator(dag=dag, input_operator=get_input, dev_server="code-server")
tag_dataset = LocalTaggingOperator(dag=dag, input_operator=train_test_split, add_tags_from_file=True, tags_to_add_from_file=["train_test_split_tag"])
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> train_test_split >> tag_dataset >> clean
