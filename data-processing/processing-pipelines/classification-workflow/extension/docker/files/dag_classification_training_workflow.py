from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from classification_training_workflow.PreprocessingOperator import PreprocessingOperator
from classification_training_workflow.TrainingOperator import TrainingOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "tag_to_class_mapping_json": {
                "title": "Tag to class mapping json",
                "description": "Specify the used tags. E.g.: ['tag0', 'tag1']",
                "default": "['CT', 'MR']",
                "type": "string",
                "required": True,
            },
            "task": {
                "title": "Classification task",
                "description": "Choose which classification task you want to train",
                "enum": ["binary", "multiclass", "multilabel"],
                "type": "string",
                "default": "binary",
                "required": True,
                "readOnly": False,
            },
            "dimensions": {
                "title": "Dimensions",
                "description": "Choose which input dimension you want to train",
                "enum": ["2D", "3D"],
                "type": "string",
                "default": "3D",
                "required": True,
                "readOnly": False,
            },
            "patch_size": {
                "title": "Patch size",
                "description": "Specify the patch size used for training",
                "default": "(128, 128, 128)",
                "type": "string",
                "required": True,
            },
            "batch_size": {
                "title": "Batch size",
                "description": "Specify the batch size used for training",
                "default": "1",
                "type": "string",
                "required": True,
            },
            "num_epochs": {
                "title": "Number of epochs",
                "description": "Specify the number of epochs used for training",
                "default": "1600",
                "type": "string",
                "required": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": True,
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

dag = DAG(
    dag_id="classification-training-workflow", default_args=args, schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input)
preprocessing = PreprocessingOperator(
    dag=dag,
    input_operator=convert,
    # dev_server='code-server'
)

training = TrainingOperator(
    dag=dag,
    input_operator=preprocessing,
    # dev_server='code-server'
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> preprocessing >> training >> clean
