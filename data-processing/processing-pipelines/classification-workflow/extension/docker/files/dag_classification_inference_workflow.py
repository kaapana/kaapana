import glob
import os
from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from classification_inference_workflow.InferenceOperator import InferenceOperator
from classification_training_workflow.PreprocessingOperator import PreprocessingOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
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
        },
    }
}


def find_tar_files(root_folder):
    # List to store the parent folder and file names
    result = []

    # Use glob to find all .tar files in the root_folder and its subdirectories
    tar_files = glob.glob(f"{root_folder}/**/*.tar", recursive=True)

    # Iterate through the list of .tar files found
    for file_path in tar_files:
        # Extract the parent folder's name
        parent_folder_name = os.path.basename(os.path.dirname(file_path))

        # Append the parent folder and file name to the list
        result.append(os.path.join(parent_folder_name, os.path.basename(file_path)))

    return result


# Starting folder
root_folder = "/kaapana/mounted/workflows/models/classification-training-workflow"

# Call the function and store the result
tar_files_with_parent = find_tar_files(root_folder)

if len(tar_files_with_parent) == 1:
    ui_forms["workflow_form"]["properties"]["model"] = {
        "title": "Model",
        "description": "Choose which model you want to use",
        "default": tar_files_with_parent[0],
        "type": "string",
        "required": True,
        "readOnly": True,
    }
else:
    ui_forms["workflow_form"]["properties"]["model"] = {
        "title": "Model",
        "description": "Choose which model you want to use",
        "enum": tar_files_with_parent,
        "type": "string",
        "required": True,
        "readOnly": False,
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
    dag_id="classification-inference-workflow",
    default_args=args,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input)
preprocessing = PreprocessingOperator(
    dag=dag,
    input_operator=convert,
    # dev_server='code-server'
)

training = InferenceOperator(
    dag=dag,
    input_operator=preprocessing,
    # dev_server='code-server'
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> preprocessing >> training >> clean
