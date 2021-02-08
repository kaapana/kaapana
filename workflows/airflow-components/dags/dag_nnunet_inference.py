from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.NnUnetOperator import NnUnetOperator
from kaapana.operators.ResampleOperator import ResampleOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from nnunet.LocalSegCheckOperator import LocalSegCheckOperator
# from nnunet.GetContainerModelOperator import GetContainerModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

import json
import os
from os.path import join, basename, dirname, normpath, exists

af_home_path = "/root/airflow"
models_path = join(af_home_path, "models", "nnUNet")
tasks_json_path = join(af_home_path, "dags", "nnunet", "nnunet_tasks.json")

with open(tasks_json_path) as f:
    tasks = json.load(f)

available_tasks = [*{k: v for (k, v) in tasks.items() if "supported" in tasks[k] and tasks[k]["supported"]}]
models_available = [basename(normpath(f.path)) for f in os.scandir(models_path) if f.is_dir() and "ensembles" not in f.name ]

print("################### Start")
for model in models_available:
    model_path = join(models_path, model)
    task_dirs = [basename(normpath(f.path)) for f in os.scandir(model_path) if f.is_dir()]
    for task in task_dirs:
        if task not in tasks:
            print(f"################### Adding task:{model}: {task}")
            model_info_path = join(model_path, task, "model_info.json")
            if exists(model_info_path):
                print(f"Found model_info.json at {model_info_path}")
                with open(model_info_path) as f:
                    model_info = json.load(f)
            else:
                print(f"Could not find model_info.json at {model_info_path}")
                model_info = {
                    "description": f"Custom model: {task}",
                    "model": [],
                    "input-mode": "all",
                    "input": ["UNKNOWN"],
                    "body_part": "UNKNOWN",
                    "targets": [
                        "UNKNOWN"
                    ],
                    "supported": True,
                    "info": "",
                    "url": "-",
                    "task_url": "-"
                }

            available_tasks.append(task)
            available_tasks.sort()
            tasks[task] = {
                "description": model_info["description"],
                "model": [],
                "input-mode": model_info["input-mode"],
                "input": model_info["input"],
                "body_part": model_info["body_part"],
                "targets": model_info["targets"],
                "supported": model_info["supported"],
                "info": model_info["info"],
                "url": model_info["url"],
                "task_url": model_info["task_url"]
            }
        if model not in tasks[task]['model']:
            tasks[task]['model'].append(model)
        tasks[task]['model'].sort()

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
                "default": False,
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "Tasks available",
                "description": "Select one of the available tasks.",
                "type": "string",
                "enum": available_tasks,
                "required": True
            },
            "description": {
                "title": "Task Description",
                "description": "Description of the task.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "task_url": {
                "title": "Website",
                "description": "Website to the task.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "input": {
                "title": "Input Modalities",
                "description": "Expected input modalities.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "body_part": {
                "title": "Body Part",
                "description": "Body part, which needs to be present in the image.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "targets": {
                "title": "Segmentation Targets",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "model": {
                "title": "Pre-trained models",
                "description": "Select one of the available models.",
                "type": "string",
                "default": "3d_lowres",
                "required": True,
                "enum": models_available,
                "dependsOn": [
                    "task"
                ]
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            }
        }
    }
}
args = {
    'ui_visible': True,
    'ui_dag_info': tasks,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-predict',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)
get_task_model = GetTaskModelOperator(dag=dag)
# get_task_model = GetContainerModelOperator(dag=dag)
dcm2nifti = DcmConverterOperator(
    dag=dag, 
    input_operator=get_input, 
    output_format='nii.gz'
    )

nnunet_predict = NnUnetOperator(
    dag=dag,
    mode="inference",
    input_nifti_operators=[dcm2nifti],
    inf_preparation=True,
    inf_threads_prep=1,
    inf_threads_nifti=1
)

resample_seg = ResampleOperator(
    dag=dag,
    input_operator=nnunet_predict,
    original_img_operator=dcm2nifti,
    operator_out_dir = nnunet_predict.operator_out_dir
)

alg_name = nnunet_predict.image.split("/")[-1].split(":")[0]
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    alg_name=alg_name
)

check_seg = LocalSegCheckOperator(
    dag=dag,
    abort_on_error=True,
    move_data=False,
    input_operators=[nrrd2dcmSeg_multi, get_input]
)

dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> get_task_model >> dcm2nifti >> nnunet_predict >> nrrd2dcmSeg_multi >> resample_seg >> check_seg >> dcmseg_send_multi >> clean
