from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

from dataclasses import dataclass, field
from nndet.NnDetOperator import NnDetOperator, Mode


max_active_runs = 5


@dataclass
class TaskParams:
    name: str
    description: str
    url: str
    input_modalities: str
    body_part: str
    det_targets: str
    pretrained_model_list: list = field(default_factory=list)
    fold_list: list = field(default_factory=["0", "1", "2", "3", "-1"])


def get_properties_dict(task_params: TaskParams):
    property_dict= {
        "task":
            {
                "type": "string",
                "const": task_params.name
            },
        "description":
            {
                "title": "Task description",
                "default": task_params.description,
                "type": "string",
                "readOnly": True
            },
        "task_url":
            {
                "title": "Website",
                "type": "string",
                "default": task_params.url,
                "readOnly": True
            },
        "input":
            {
                "title": "Input Modalities",
                "type": "string",
                "default": task_params.input_modalities,
                "readOnly": True
            },
        "body_part":
            {
                "title": "Body Part",
                "description": "Body part, which needs to be present in the image.",
                "type": "string",
                "default": task_params.body_part,
                "readOnly": True
            },
        "targets":
            {
                "title": "Detection Targets",
                "type": "string",
                "default": task_params.det_targets,
                "readOnly": True
            },
        "model":
            {
                "title": "Pre-trained models",
                "description": "Select one of the available models.",
                "type": "string",
                "required": True,
                "enum": task_params.pretrained_model_list
            },
        "fold":
            {
                "title": "Fold",
                "description": "Select fold",
                "type": "string",
                "enum": task_params.fold_list,
                "readOnly": False,
                "required": True
            },
        "single_execution":
            {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False
            }
                            
        }
    return property_dict

def get_publication_dict():
    return {
            "type": "object",
            "properties":
                {
                    "title": {
                        "title": "Title",
                        "default": "nnDetection: A Self-configuring Method for Medical Object Detection",
                        "type": "string",
                        "readOnly": True,
                    },
                    "authors": {
                        "title": "Authors",
                        "default": "Michael Baumgartner, Paul F. Jäger, Fabian Isensee, Klaus H. Maier-Hein",
                        "type": "string",
                        "readOnly": True,
                    },
                    "link": {
                        "title": "DOI",
                        "default": "https://doi.org/10.1007/978-3-030-87240-3_51",
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
            }

def get_workflow_dict():
    
    task_params = TaskParams(name="Task000D3_Example",
                             description="nndet example",
                             url="https://github.com/MIC-DKFZ/nnDetection",
                             input_modalities="toy_data",
                             body_part="None",
                             det_targets="noisy rectangles",
                             pretrained_model_list=["RetinaUNetV001_D3V001_3d", "placeholder"],
                             fold_list=["1", "2"])
    
    
    return {
            "type": "object",
            "title": "Tasks available",
            "description": "Select one of the available tasks.",
            "oneOf": [{
                        "title": task_params.name,
                        "properties": get_properties_dict(task_params)
                    }#,
                    #{
                    #    "title": "task_place_holder",
                    #    "properties": property_dict_template
                    #}
                    ]
            }

ui_forms = {
    "publication_form": get_publication_dict(),
    "workflow_form": get_workflow_dict()
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nndet-predict',
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format='nii.gz'
)

nndet_inference = NnDetOperator(
    dag=dag,
    mode=Mode.INFERENCE,
    input_operator=dcm2nifti
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name='upload-nndet-inference',
    zip_files=True,
    action='put',
    action_operators=[nndet_inference],
    file_white_tuples=('.zip')
)



clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2nifti >> nndet_inference >> put_to_minio >> clean
