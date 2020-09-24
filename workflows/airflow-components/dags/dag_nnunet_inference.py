from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime

# from nnunet.LocalSplitLabelOperator import LocalSplitLabelOperator
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmWebSendOperator import DcmWebSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

import pathlib
import json
import os

# dcmsend e230-pc02 -v 11112 -aet PUSH_TOOL -aec "CTPET" --scan-directories --scan-pattern *.dcm --recurse ./DicomExportService/
# wget "https://zenodo.org/record/3734294/files/Task017_AbdominalOrganSegmentation.zip?download=1" -O "./Task017_AbdominalOrganSegmentation.zip"
# mkdir -p /home/kaapana/data/workflows/models/nnUNet
# unzip ./Task017_AbdominalOrganSegmentation.zip -d "/home/kaapana/data/workflows/models/nnUNet"

tasks_json_path = os.path.join("/root/airflow/dags","nnunet","nnunet_tasks.json")
with open(tasks_json_path) as f:
    tasks = json.load(f)

available_tasks = [*{k:v for (k,v) in tasks.items() if "supported" in tasks[k] and tasks[k]["supported"]}]
available_models = [*tasks["Task001_BrainTumour"]["models"]]

task_models_present = []
for task_id in available_tasks:
    model_path = os.path.join("/root/airflow/models/nnUNet/2d", task_id)
    if os.path.isdir(model_path):
        task_models_present.append(task_id)

print(task_models_present)

dag_info = {
    "visible": True,
    "modality": ["CT","MRI"],
    "publication": {
        "doi": "arXiv preprint: 1904.08128 (2020)",
        "link": "https://github.com/MIC-DKFZ/nnUNet",
        "title": "Automated Design of Deep Learning Methods for Biomedical Image Segmentation",
        "authors": "Fabian Isensee, Paul F. J\xc3\xa4ger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
        "confirmation": False
    },
    "form_schema": {
        "$schema": "http://json-schema.org/draft-03/schema#",
        "type": "object",
        "properties": {
            "task": {
                "title": "Tasks available",
                "description": "Select one of the available tasks.",
                "type": "string",
                "enum": available_tasks,
                "required": 'true'
            },
            "model": {
                "title": "Pre-trained models",
                "description": "Select one of the available models.",
                "type": "string",
                "enum": available_models,
                "required": 'true'
            },
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


dcmseg_send_multi = DcmWebSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> get_task_model >> dcm2nifti >> nnunet_predict >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
