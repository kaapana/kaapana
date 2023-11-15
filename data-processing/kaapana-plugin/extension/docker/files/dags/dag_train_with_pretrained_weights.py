import random
from datetime import datetime, timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator
from kaapana.blueprints.kaapana_global_variables import (
    GPU_COUNT,
)
from kaapana.blueprints.kaapana_global_variables import (
    INSTANCE_NAME,
    GPU_COUNT,
)
from dag_nnunet_training import ui_forms as nnunet_form
from dag_classification_training_workflow import ui_forms as clf_form

max_active_runs = GPU_COUNT if GPU_COUNT != 0 else 1
print(f"### max_active_runs {max_active_runs}")

# TODO: assign selected DAG value here
default_training_dag = ""

# TODO: fetch names from installed DAGs
training_dags = ["nnunet-training", "classification-training-workflow"]

ui_forms = {
    "workflow_form": {
        "type": "object",
        "title": "Training Workflow",
        "description": "Select which training workflow to pass the pretrained weights",
        "oneOf": []
    }
}

# TODO: append publication form from nnunet
# TODO: if first nnunet is chosen and then clf, the field "task" is overwritten by nnunet value
for training_dag in training_dags:
    selection = {
        "title": training_dag,
        "properties": {"default_training_dag": {"type": "string", "const": training_dag}}
    }
    # prepare the DAG specific form, new training workflows should also be added here
    if training_dag == "nnunet-training":
        study_id = "Kaapana"
        TASK_NAME = f"Task{random.randint(100,999):03}_{INSTANCE_NAME}_{datetime.now().strftime('%d%m%y-%H%M')}"
        default_model = "3d_lowres"
        train_network_trainer = "nnUNetTrainerV2"
        prep_modalities = "CT"
        seg_filter = ""
        max_epochs = 1000
        num_batches_per_epoch = 250
        num_val_batches_per_epoch = 50
        ae_title = "nnUnet-training-results"
        dicom_model_slice_size_limit = 70
        training_results_study_uid = None
        prep_threads = 2

        # TODO: put additional "pretrained_weights" and "folds" fields here with all the installed tasks
        for k, v in nnunet_form["workflow_form"]["properties"].items():
            selection["properties"][k] = v
        
        ui_forms["workflow_form"]["oneOf"].append(selection)

    elif training_dag == "classification-training-workflow":
        for k, v in clf_form["workflow_form"]["properties"].items():
            selection["properties"][k] = v
        
        ui_forms["workflow_form"]["oneOf"].append(selection)

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="train-with-pretrained-weights",
    default_args=args,
    concurrency=2 * max_active_runs,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

dag_trigger_operator = LocalDagTriggerOperator(
    dag=dag,
    trigger_dag_id="nnunet-training",
    input_operator=None,
    trigger_mode="single",
    wait_till_done=True,
    delay=10
)

dag_trigger_operator