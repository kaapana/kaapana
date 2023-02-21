import copy
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.getTasks import get_tasks
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

max_active_runs = 10
concurrency = max_active_runs * 2
default_interpolation_order = "default"
default_prep_thread_count = 1
default_nifti_thread_count = 1

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
        "required": True
    },
    "inf_threads_prep": {
        "title": "Pre-processing threads",
        "type": "integer",
        "default": default_prep_thread_count,
        "description": "Set pre-processing thread count.",
        "required": True
    },
    "inf_threads_nifti": {
        "title": "NIFTI threads",
        "type": "integer",
        "description": "Set NIFTI export thread count.",
        "default": default_nifti_thread_count,
        "required": True
    },
    "single_execution": {
        "title": "single execution",
        "description": "Should each series be processed separately?",
        "type": "boolean",
        "default": True,
        "readOnly": False,
    }
}

workflow_form = {
    "type": "object",
    "title": "Tasks available",
    "description": "Select one of the available tasks.",
    "oneOf": []
}

for idx, (task_name, task_values) in enumerate(all_selectable_tasks.items()):
    task_selection = {
        "title": task_name,
        "properties": {
            "task": {
                "type": "string",
                "const": task_name
            }
        }
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
                "default": False,
                "type": "boolean",
                "readOnly": False,
                "required": True,
            }
        }
    }
}
ui_forms["workflow_form"] = workflow_form

args = {
    'ui_visible': True,
    'ui_dag_info': all_selectable_tasks,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-predict',
    default_args=args,
    concurrency=concurrency,
    max_active_runs=max_active_runs,
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
    input_modality_operators=[dcm2nifti],
    inf_threads_prep=2,
    inf_threads_nifti=2,
    execution_timeout = timedelta(minutes=30)
)

alg_name = nnunet_predict.image.split("/")[-1].split(":")[0]
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    skip_empty_slices=True,
    alg_name=alg_name
)

dcmseg_send_multi = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_task_model >> nnunet_predict
get_input >> dcm2nifti >> nnunet_predict >> nrrd2dcmSeg_multi >> dcmseg_send_multi >> clean
