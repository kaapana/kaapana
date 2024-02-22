import copy
import glob
import os
from pathlib import Path
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.getTasks import get_tasks
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.GetZenodoModelOperator import GetZenodoModelOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR
from airflow.operators.python import BranchPythonOperator

from nnunet.LocalCreateEmptySegmentsOperator import (
    get_all_files_from_dir,
    LocalCreateEmptySegmentsOperator,
)

max_active_runs = 10
concurrency = max_active_runs * 2
default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
ae_title = "nnUnet-predict-results"
available_pretrained_task_names, installed_tasks, all_selectable_tasks = get_tasks()

properties_template = {
    "description": {
        "title": "Task Description",
        "description": "Description of the task.",
        "type": "string",
        "readOnly": True,
    },
    "task_url": {
        "title": "Website",
        "description": "Website to the task.",
        "type": "string",
        "readOnly": True,
    },
    "input": {
        "title": "Input Modalities",
        "description": "Expected input modalities.",
        "type": "string",
        "readOnly": True,
    },
    "body_part": {
        "title": "Body Part",
        "description": "Body part, which needs to be present in the image.",
        "type": "string",
        "readOnly": True,
    },
    "targets": {
        "title": "Segmentation Targets",
        "type": "string",
        "readOnly": True,
    },
    "model": {
        "title": "Pre-trained models",
        "description": "Select one of the available models.",
        "type": "string",
        "required": True,
        "enum": [],
    },
    "inf_softmax": {
        "title": "enable softmax",
        "description": "Enable softmax export?",
        "type": "boolean",
        "default": False,
        "readOnly": False,
    },
    "interpolation_order": {
        "title": "interpolation order",
        "default": default_interpolation_order,
        "description": "Set interpolation_order.",
        "enum": ["default", "0", "1", "2", "3"],
        "type": "string",
        "readOnly": False,
        "required": True,
    },
    "inf_threads_prep": {
        "title": "Pre-processing threads",
        "type": "integer",
        "default": default_prep_thread_count,
        "description": "Set pre-processing thread count.",
        "required": True,
    },
    "inf_threads_nifti": {
        "title": "NIFTI threads",
        "type": "integer",
        "description": "Set NIFTI export thread count.",
        "default": default_nifti_thread_count,
        "required": True,
    },
    "single_execution": {
        "title": "single execution",
        "description": "Should each series be processed separately?",
        "type": "boolean",
        "default": True,
        "readOnly": False,
    },
    "allow_empty_segmentation": {
        "title": "Allow Empty Segmentation",
        "description": "handle the cases if the model fails to detect any segmentation and produces a empty segmentation nifti file",
        "type": "boolean",
        "default": True,
    },
    "empty_segmentation_label": {
        "title": "Empty Segmentation Label",
        "type": "integer",
        "description": "Replace the empty segmentation mask with the user given mask label",
        "default": 99,
    },
}

workflow_form = {
    "type": "object",
    "title": "Tasks available",
    "description": "Select one of the available tasks.",
    "oneOf": [],
}

for idx, (task_name, task_values) in enumerate(all_selectable_tasks.items()):
    task_selection = {
        "title": task_name,
        "properties": {"task_ids": {"type": "string", "const": task_name}},
    }
    task_properties = copy.deepcopy(properties_template)
    for key, item in task_properties.items():
        if key in task_values:
            to_be_placed = task_values[key]
            if key == "model":
                item["enum"] = to_be_placed
            else:
                if isinstance(to_be_placed, list):
                    to_be_placed = ",".join(to_be_placed)
                item["default"] = to_be_placed
    for key in list(properties_template.keys()):
        task_properties[f"{key}#{idx}"] = task_properties.pop(key)

    task_selection["properties"].update(task_properties)
    workflow_form["oneOf"].append(task_selection)


ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "Automated Design of Deep Learning Methods\n for Biomedical Image Segmentation",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/1904.08128",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                # "default": False,
                "type": "boolean",
                "readOnly": False,
                "required": True,
            },
        },
    }
}
ui_forms["workflow_form"] = workflow_form

args = {
    "ui_visible": True,
    "ui_dag_info": all_selectable_tasks,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="miac-nnunet-flow",
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(
    dag=dag, parallel_downloads=5, check_modality=True
)
get_task_model = GetZenodoModelOperator(dag=dag)
dcm2nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

nnunet_predict = NnUnetOperator(
    dag=dag,
    mode="inference",
    input_modality_operators=[dcm2nifti],
    inf_threads_prep=2,
    inf_threads_nifti=2,
    execution_timeout=timedelta(minutes=30),
)

create_empty_segments = LocalCreateEmptySegmentsOperator(
    dag=dag,
    name="create-empty-segmentation",
    input_operator=dcm2nifti,
    operator_out_dir=nnunet_predict.operator_out_dir,
)


alg_name = nnunet_predict.image.split("/")[-1].split(":")[0]
meta_props = {
    "ContentLabel": "SEGMENTATION_HD-BET",
    "ContentDescription": "Image segmentation",
    "ClinicalTrialCoordinatingCenterName": "MIAC",
}
# segment_attributes_props = {
#     '99': ('recommendedDisplayRGBValue', [0, 0, 128]),
#     '0': ('recommendedDisplayRGBValue', [66, 77, 128]),
# }

segment_attributes_props = {
    "SegmentLabel": "Empty Mask",
    "recommendedDisplayRGBValue": "[66, 77, 128]",
}

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    skip_empty_slices=True,
    alg_name=alg_name,
    meta_json_props=meta_props,
    seg_attrs_props=segment_attributes_props,
    trigger_rule="none_failed_min_one_success",
    dev_server="code-server",
)


def segmentation_file_check_callable(**kwargs):
    conf = kwargs["dag_run"].conf

    # Retrieve the run directory based on the DAG run ID
    run_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id
    # Gather the output batch directories for processing
    batch_dirs = [
        f
        for f in glob.glob(os.path.join(run_dir, create_empty_segments.batch_name, "*"))
    ]

    seg_file_in_all_batches = True
    # Iterate through each batch directory
    for batch_element in batch_dirs:
        input_files_dir = os.path.join(
            batch_element, create_empty_segments.operator_out_dir
        )

        # Retrieve all files in the input directory matching the NIfTI file format
        all_nifties = get_all_files_from_dir(
            input_files_dir, filter_pattern=r".*\.nii.*"
        )

        if len(all_nifties) == 0:
            seg_file_in_all_batches = False
            break

    if not seg_file_in_all_batches:
        return [create_empty_segments.name]
    else:
        return [nrrd2dcmSeg_multi.name]


check_if_segmentaion_exists = BranchPythonOperator(
    task_id="check-if-segmentation-exists",
    provide_context=True,
    python_callable=segmentation_file_check_callable,
    dag=dag,
    depends_on_past=False,
)

dcmseg_send_multi = DcmSendOperator(
    dag=dag, ae_title=ae_title, input_operator=nrrd2dcmSeg_multi
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_task_model >> nnunet_predict
(get_input >> dcm2nifti >> nnunet_predict >> check_if_segmentaion_exists)

check_if_segmentaion_exists >> create_empty_segments >> nrrd2dcmSeg_multi
check_if_segmentaion_exists >> nrrd2dcmSeg_multi

nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
