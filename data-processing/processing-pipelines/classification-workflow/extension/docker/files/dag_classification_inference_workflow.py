from datetime import timedelta

from airflow.models import DAG
from airflow.operators.empty import EmptyOperator
from airflow.utils.dates import days_ago
from classification_inference_workflow.InferenceOperator import InferenceOperator
from classification_training_workflow.PreprocessingOperator import PreprocessingOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

properties_template = {
    "description": {
        "title": "Model Description",
        "type": "string",
        "readOnly": True,
    },
    "targets": {
        "title": "Classification Targets",
        "type": "string",
        "readOnly": True,
    },
    "task": {
        "title": "Classification Task",
        "type": "string",
        "readOnly": True,
    },
    "task_ids": {
        "title": "Model ID",
        "type": "string",
        "readOnly": True,
    },
    "tag_postfix": {
        "title": "tag postfix",
        "description": "Give the inference tag the model ID as postfix",
        "type": "boolean",
        "default": False,
        "readOnly": False,
    },
    "single_execution": {
        "title": "single execution",
        "description": "Should each series be processed separately?",
        "type": "boolean",
        "default": False,
        "readOnly": False,
    },
}

workflow_form = {
    "type": "object",
    "title": "Models available",
    "description": "Select one of the available classification models.",
    "oneOf": [],
    "properties-template": properties_template,
    "models": True,
    "kind": "classification",
}

ui_forms = {
    "workflow_form": workflow_form,
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="classification-inference",
    default_args=args,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input)
preprocessing = PreprocessingOperator(
    dag=dag,
    input_operator=convert,
)

inference = InferenceOperator(
    dag=dag,
    input_operator=preprocessing,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True, trigger_rule="all_done")


check_success = EmptyOperator(task_id="check-success", dag=dag, trigger_rule="none_failed")
get_input >> convert >> preprocessing >> inference >> [clean, check_success]
