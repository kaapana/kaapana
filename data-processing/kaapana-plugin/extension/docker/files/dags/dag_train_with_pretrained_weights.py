import random
from datetime import datetime, timedelta
from glob import glob

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

max_active_runs = GPU_COUNT if GPU_COUNT != 0 else 1
print(f"### max_active_runs {max_active_runs}")

training_dags = []
try:
    from dag_nnunet_training import ui_forms as nnunet_form
    from nnunet.getTasks import get_all_checkpoints

    training_dags.append("nnunet-training")
except Exception as e:
    print("nnunet-training is not installed")
try:
    from dag_classification_training_workflow import ui_forms as clf_form
    from classification_training_workflow.getCheckpoints import getCheckpoints

    training_dags.append("classification-training-workflow")
except Exception as e:
    print("classification-training-workflow is not installed")

ui_forms = {
    "workflow_form": {
        "type": "object",
        "title": "Training Workflow",
        "description": "Select which training workflow to pass the pretrained weights",
        "oneOf": [],
    }
}

# TODO: append publication form from nnunet
# TODO: if first nnunet is chosen and then clf, the field "task" is overwritten by nnunet value
for training_dag in training_dags:
    selection = {
        "title": training_dag,
        "properties": {
            "trigger_dag_id": {"type": "string", "const": training_dag},
            "pretrained_weights": {
                "type": "string",
                "title": "Model checkpoints available",
                "default": "",
                "description": "",
                "enum": [],
            },
        },
    }

    # prepare the DAG specific form, new training workflows should also be added here
    if training_dag == "nnunet-training":
        study_id = "Kaapana"
        TASK_NAME = f"Task{random.randint(100,999):03}_{INSTANCE_NAME}_{datetime.now().strftime('%d%m%y-%H%M')}"
        default_model = "3d_lowres"
        train_network_trainer = "nnUNetTrainerV2_Loss_DiceCE_noSmooth_warmupSegHeads"
        prep_modalities = "CT"
        seg_filter = ""
        max_epochs = 1000
        num_batches_per_epoch = 250
        num_val_batches_per_epoch = 50
        ae_title = "pretrained-nnUnet-training-results"
        dicom_model_slice_size_limit = 70
        training_results_study_uid = None
        prep_threads = 2

        # add pretrained weights options
        checkpoints = get_all_checkpoints()

        val = selection["properties"]["pretrained_weights"]
        val[
            "description"
        ] = "Select pretrained weights from installed tasks. Use nnunet-model-management DAG to install more tasks. NOTE: please select the right 'network/task/trainer/fold' combination for your training, otherwise it will fail."
        for checkpoint in checkpoints:
            val["enum"].append(checkpoint)

        # add the workflow_form
        for k, v in nnunet_form["workflow_form"]["properties"].items():
            selection["properties"][k] = v

        ui_forms["workflow_form"]["oneOf"].append(selection)

    elif training_dag == "classification-training-workflow":
        # add pretrained weights options
        checkpoints = getCheckpoints()

        val = selection["properties"]["pretrained_weights"]
        val[
            "description"
        ] = "Select pretrained weights from previous classification training runs"
        for checkpoint in checkpoints:
            val["enum"].append(checkpoint)

        # add the workflow_form
        for k, v in clf_form["workflow_form"]["properties"].items():
            selection["properties"][k] = v

        ui_forms["workflow_form"]["oneOf"].append(selection)

    else:
        print(f"Unknown training DAG {training_dag}")


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

# TODO: triggers as a service DAG
dag_trigger_operator = LocalDagTriggerOperator(
    dag=dag,
    trigger_dag_id="",  # operator gets from workflow_form.trigger_dag_id , only for use_dcm_files=False
    use_dcm_files=False,
    input_operator=None,
    trigger_mode="single",
    wait_till_done=True,
    delay=10,
)

dag_trigger_operator
