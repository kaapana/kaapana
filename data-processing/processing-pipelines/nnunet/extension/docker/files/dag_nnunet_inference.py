import copy
from datetime import datetime, timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.NnUnetOperator import NnUnetOperator

max_active_runs = 10
concurrency = max_active_runs * 2
default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1
ae_title = "nnUnet-predict-results"


properties_template = {
    "description": {
        "title": "Task Description",
        "description": "Description of the task.",
        "type": "string",
        "readOnly": True,
    },
    "model_name": {
        "title": "Model Description",
        "description": "Description of the model.",
        "type": "string",
        "readOnly": True,
    },
    "instance_name": {
        "title": "Instance Name",
        "description": "Name of the central instance.",
        "type": "string",
        "readOnly": True,
    },
    "model_network_trainer": {
        "title": "Model Network Trainer",
        "description": "Trainer used to train the network.",
        "type": "string",
        "readOnly": True,
    },
    "model_plan": {
        "title": "Model Plan",
        "description": "Plan user to train the network.",
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
}

workflow_form = {
    "type": "object",
    "title": "Tasks available",
    "description": "Select one of the available tasks.",
    "oneOf": [],
    "properties-template": properties_template,
    "models": True,
}

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#nnunet-predict",
    },
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
    },
}
ui_forms["workflow_form"] = workflow_form

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="nnunet-predict",
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(
    dag=dag, parallel_downloads=5, check_modality=True
)
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

alg_name = nnunet_predict.image.split("/")[-1].split(":")[0]
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    skip_empty_slices=True,
    alg_name=alg_name,
)

dcmseg_send_multi = DcmSendOperator(
    dag=dag, ae_title=ae_title, input_operator=nrrd2dcmSeg_multi
)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

(
    get_input
    >> dcm2nifti
    >> nnunet_predict
    >> nrrd2dcmSeg_multi
    >> dcmseg_send_multi
    >> clean
)
