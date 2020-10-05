from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime

# from nnunet.LocalSplitLabelOperator import LocalSplitLabelOperator
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

import pathlib
import json
import os

tasks_json_path = os.path.join("/root/airflow/dags", "nnunet", "nnunet_tasks.json")
with open(tasks_json_path) as f:
    tasks = json.load(f)

available_tasks = [*{k: v for (k, v) in tasks.items() if "supported" in tasks[k] and tasks[k]["supported"]}]
available_models = [*tasks["Task001_BrainTumour"]["models"]]

dag_info = {
    "visible": True,
    "tasks": tasks,
    "modality": ["CT", "MRI"],
    "publication": {
        "doi": "arXiv preprint: 1904.08128 (2020)",
        "link": "https://github.com/MIC-DKFZ/nnUNet",
        "title": "Automated Design of Deep Learning Methods for Biomedical Image Segmentation",
        "authors": "Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
        "confirmation": False
    },
    "form_schema": {
        "type": "object",
        "properties": {
            "task": {
                "index": "1",
                "title": "Tasks available",
                "description": "Select one of the available tasks.",
                "type": "string",
                "enum": available_tasks,
                "required": "true"
            },
            "description": {
                "index": "2",
                "title": "Task Description",
                "description": "Description of the task.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "url": {
                "index": "3",
                "title": "Website",
                "description": "Website to the task.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "body_part": {
                "index": "4",
                "title": "Body Part",
                "description": "Body part, which needs to be present in the image.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "input-mode": {
                "index": "5",
                "title": "Input Mode",
                "description": "Input mode expected.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "input": {
                "index": "6",
                "title": "Input Modalities",
                "description": "Expected input modalities.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "targets": {
                "index": "7",
                "title": "Segmentation Targets",
                "description": "Segmentation targets.",
                "type": "string",
                "readOnly": True,
                "dependsOn": [
                    "task"
                ]
            },
            "models": {
                "index": "8",
                "title": "Pre-trained models",
                "description": "Select one of the available models.",
                "type": "string",
                "default": "3d_lowres",
                "enum": [],
                "dependsOn": [
                    "task"
                ]
            }
        }
    }
}
args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-predict',
    default_args=args,
    schedule_interval=None
)

get_task_model = GetTaskModelOperator(dag=dag)
get_input = LocalGetInputDataOperator(dag=dag)
dcm2nifti = DcmConverterOperator(dag=dag, output_format='nii.gz')
nnunet_predict = NnUnetOperator(dag=dag, input_dirs=[dcm2nifti.operator_out_dir], input_operator=dcm2nifti)

alg_name = "nnUnet-{}".format(nnunet_predict.image.split(":")[1])
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    alg_name=alg_name
)


dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> get_task_model >> dcm2nifti >> nnunet_predict >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
