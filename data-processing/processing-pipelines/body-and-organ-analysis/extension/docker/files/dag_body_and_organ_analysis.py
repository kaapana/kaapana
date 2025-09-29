from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.exceptions import AirflowSkipException
from airflow.utils.state import State
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.KaapanaBranchPythonBaseOperator import (
    KaapanaBranchPythonBaseOperator,
)
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from body_and_organ_analysis.BodyAndOrganAnalysisOperator import (
    BodyAndOrganAnalysisOperator,
)
from body_and_organ_analysis.BoaOutputCheckOperator import (
    BoaOutputCheckOperator,
)

from os.path import join
from os import environ

max_active_runs = 5


ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#body-and-organ-analysis",
    },
    "publication_form": {
        "type": "object",
        "properties": {
            "boa": {
                "title": "BOA",
                "default": "Haubold, J., Baldini, G., Parmar, V., Schaarschmidt, B. M., Koitka, S., Kroll, L., van Landeghem, N., Umutlu, L., Forsting, M., Nensa, F., & Hosch, R. (2023). BOA: A CT-Based Body and Organ Analysis for Radiologists at the Point of Care. Investigative radiology, 10.1097/RLI.0000000000001040. Advance online publication. https://doi.org/10.1097/RLI.0000000000001040",
                "description": "Haubold, J., Baldini, G., Parmar, V., Schaarschmidt, B. M., Koitka, S., Kroll, L., van Landeghem, N., Umutlu, L., Forsting, M., Nensa, F., & Hosch, R. (2023). BOA: A CT-Based Body and Organ Analysis for Radiologists at the Point of Care. Investigative radiology, 10.1097/RLI.0000000000001040. Advance online publication. https://doi.org/10.1097/RLI.0000000000001040",
                "type": "string",
                "readOnly": True,
            },
            "totalsegmentator": {
                "title": "TotalSegmentator",
                "default": "Wasserthal J, Breit H-C, Meyer MT, et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. Radiol. Artif. Intell. 2023:e230024. Available at: https://pubs.rsna.org/doi/10.1148/ryai.230024.",
                "description": "Wasserthal J, Breit H-C, Meyer MT, et al. TotalSegmentator: Robust Segmentation of 104 Anatomic Structures in CT Images. Radiol. Artif. Intell. 2023:e230024. Available at: https://pubs.rsna.org/doi/10.1148/ryai.230024.",
                "type": "string",
                "readOnly": True,
            },
            "nnunet": {
                "title": "nnU-Net",
                "default": "Isensee F, Jaeger PF, Kohl SAA, et al. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat. Methods. 2021;18(2):203–211. Available at: https://www.nature.com/articles/s41592-020-01008-z.",
                "description": "Isensee F, Jaeger PF, Kohl SAA, et al. nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation. Nat. Methods. 2021;18(2):203–211. Available at: https://www.nature.com/articles/s41592-020-01008-z.",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": False,
                "required": True,
                "description": "I will cite the publications above if applicable.",
            },
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "models": {
                "title": "Model selection",
                "description": "Select the models that should be used during analysis.",
                "type": "array",
                "minItems": 1,
                "items": {
                    "type": "string",
                    "examples": [
                        "body",
                        "total",
                        "lung_vessels",
                        "cerebral_bleed",
                        "hip_implant",
                        "coronary_arteries",
                        "pleural_pericard_effusion",
                        "liver_vessels",
                        "bca",
                    ],
                },
                "default": ["bca"],
                "readOnly": False,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": True,
            },
            "input": {
                "title": "Input modality",
                "default": "CT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
                "required": True,
            },
        },
    },
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="body-and-organ-analysis",
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5, check_modality=False)

dcm2nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

boa = BodyAndOrganAnalysisOperator(dag=dag, input_operator=dcm2nifti)

boa_check = BoaOutputCheckOperator(dag=dag, input_operator=boa)

# --- Mapping model to its outputs ---
model_outputs = {
    "body": ["body_extremities", "body_trunc"],
    "total": ["total", "pulmonary_fat"],
    "lung_vessels": ["lung_vessels_airways"],
    "cerebral_bleed": ["cerebral_bleed"],
    "hip_implant": ["hip_implant"],
    "coronary_arteries": ["coronary_arteries"],
    "pleural_pericard_effusion": ["pleural_pericard_effusion"],
    "liver_vessels": ["liver_vessels"],
    "bca": ["body-parts", "body-regions", "tissues", "vertebrae"],
}


# --- merg validation function ---
def merge_conditionally(**kwargs):
    ti = kwargs["ti"]
    dag_run = kwargs["dag_run"]

    upstream_task_ids = ti.task.upstream_task_ids

    failed_tasks = []
    succeeded_tasks = []

    for task_id in upstream_task_ids:
        task_instance = dag_run.get_task_instance(task_id)
        task_state = task_instance.current_state()
        if task_state == State.FAILED or task_state == State.UPSTREAM_FAILED:
            failed_tasks.append(task_id)
        elif task_state == State.SUCCESS:
            succeeded_tasks.append(task_id)

    if failed_tasks:
        print(f"Failed upstream tasks: {failed_tasks}")
    else:
        print("No upstream tasks failed.")

    if succeeded_tasks:
        print(f"Succeeded upstream tasks: {succeeded_tasks}")
    else:
        print("No upstream tasks succeeded.")

    if not succeeded_tasks:
        raise AirflowSkipException("No upstream tasks succeeded, skipping merge.")


# --- Branching function ---
def branch_models_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    selected_models = conf["workflow_form"].get("models", [])
    branches = []

    for model in selected_models:
        outputs = model_outputs.get(model, [])
        for out in outputs:
            task_id = f"{model}_{out}_seg2dcm" if out != model else f"{model}_seg2dcm"
            branches.append(task_id)

    return branches


# --- Branching operator ---
branch_models = KaapanaBranchPythonBaseOperator(
    name="branch_models",
    python_callable=branch_models_callable,
    dag=dag,
)

push_to_minio = MinioOperator(
    dag=dag,
    none_batch_input_operators=[boa],
    whitelisted_file_extensions=[".json", ".xlsx", ".pdf"],
    # whitelisted_file_extensions=[".json",".xlsx",".pdf",".nii.gz"]
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

# --- Static task flow up to branching and upload of other files ---
get_input >> dcm2nifti >> boa >> boa_check >> branch_models
boa >> push_to_minio >> clean

# --- Output task dictionaries ---
seg_tasks = {}
send_tasks = {}

seg_merge = KaapanaPythonBaseOperator(
    dag=dag,
    trigger_rule="all_done",
    name="merge_dcm_send",
    python_callable=merge_conditionally,
)

# --- Generate all possible segmentation/send tasks for each model output ---
for model, outputs in model_outputs.items():
    for output in outputs:
        suffix = output if output != model else ""
        task_id_prefix = f"{model}_{suffix}" if suffix else model

        seg_task_id = f"{task_id_prefix}_seg2dcm"
        send_task_id = f"{task_id_prefix}_dcm_send"

        seg_info_json = f"{output}_seg_info.json" if output != "default" else ""

        seg_task = Itk2DcmSegOperator(
            dag=dag,
            task_id=seg_task_id,
            segmentation_in_dir=join(boa_check.operator_out_dir, output),
            input_type="multi_label_seg",
            input_operator=get_input,
            skip_empty_slices=True,
            multi_label_seg_name=f"{dag.dag_id}_{task_id_prefix}",
            multi_label_seg_info_json=seg_info_json,
            alg_name=dag.dag_id,
            series_description=f"{dag.dag_id}-{output}",
            single_label_seg_info="from_file_name",
        )

        send_task = DcmSendOperator(
            dag=dag,
            task_id=send_task_id,
            input_operator=seg_task,
        )

        # Store for possible use/reference
        seg_tasks[seg_task_id] = seg_task
        send_tasks[send_task_id] = send_task

        # Set dependencies
        branch_models >> seg_task >> send_task >> seg_merge

seg_merge >> clean
