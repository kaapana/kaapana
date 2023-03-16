from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.Itk2DcmOperator import Itk2DcmOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR

from pathlib import Path

objects = HelperMinio.list_objects(HelperMinio.minioClient,
    "uploads", prefix="itk", recursive=True,
)

object_names = [obj.object_name for obj in objects]
itk_zip_objects = [object_name for object_name in object_names if object_name.endswith(".zip")]

itk_directories = []
for object_name in object_names:
    object_directory = str(Path(object_name).parents[0])
    if not object_directory.endswith(("imagesTr", "imagesTs", "labelsTr", "labelsTs", "cases", "segs")):
        itk_directories.append(str(Path(object_name).parents[0]))

# Todo add object either or 
ui_forms = {
    "data_form": {
        "type": "object",
        "title": "Select file or folder from Minio",
        "description": "The uplods/itk directory in Minio is crawled for zip files and folders",
        "properties": {
            "bucket_name": {
                "title": "Bucket name",
                "description": "Bucket name from MinIO",
                "type": "string",
                "default": "uploads",
                "readOnly": True
            }
        },
        "oneOf": [
            {
                "title": "Search for files",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "const": "files"
                    },
                    "action_files":  {
                        "title": "ZIP files from bucket",
                        "description": "Relative paths to zip file in Bucket",
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": itk_zip_objects
                        },
                        "readOnly": False
                    }
                }
            },
            {
                "title": "Search for folders",
                "properties": {
                    "identifier": {
                        "type": "string",
                        "const": "folders"
                    },
                    "action_operator_dirs": {
                        "title": "Directories",
                        "description": "Directory from bucket",
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": list(set(itk_directories))
                        },
                        "readOnly": False
                    }
                }
            }
        ]
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "modality":{
                "title": "Modality",
                "description": "Modality of the input images. Usually CT or MR.",
                "type": "string",
                "default": "",
                "required": False,
            },
            "aetitle": {
                "title": "Dataset tag",
                "description": "Specify a tag for your dataset.",
                "type": "string",
                "default": "itk2dcm",
                "required": True
            },
            "delete_original_file": {
                "title": "Delete file from Minio after successful upload?",
                "type": "boolean",
                "default": True,
            }
        }
    }
}

log = LoggingMixin().log

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='dag-convert-itk2dcm',
    default_args=args,
    schedule_interval=None
    )


get_object_from_minio = LocalMinioOperator(
    action='get',
    dag=dag,
    operator_out_dir="itk")

unzip_files = ZipUnzipOperator(
    dag=dag,
    input_operator=get_object_from_minio,
    #operator_out_dir="itk",
    batch_level=True,
    mode="unzip"
)
    
convert = Itk2DcmOperator(
    dag=dag, 
    name="convert-itk2dcm", 
    # dev_server='code-server',
    trigger_rule="none_failed_min_one_success",
    input_operator=unzip_files
) 

convert_seg = Itk2DcmSegOperator(
    dag=dag,
    name="convert-segmentation",
    input_operator=convert,
    segmentation_in_dir='segmentations', 
    input_type="multi_label_seg",
    skip_empty_slices=True,
    fail_on_no_segmentation_found=False
    # dev_server='code-server',
)

dcm_send_seg = DcmSendOperator(
    name="dcm-send-seg",
    dag=dag,
    input_operator=convert_seg
)

dcm_send_img = DcmSendOperator(
    name="dcm-send-img",
    dag=dag,
    input_operator=convert,
)

remove_object_from_minio = LocalMinioOperator(
    dag=dag,
    name='removing-object-from-minio',
    action='remove'
)

clean = LocalWorkflowCleanerOperator(dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=True)

def branching_zipping(**kwargs):
    download_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs['dag_run'].run_id / get_object_from_minio.operator_out_dir
    conf = kwargs['dag_run'].conf
    if "action_files" in conf["data_form"]:
        return [unzip_files.name]
    else:
        unzip_dir = download_dir.parents[0] / unzip_files.operator_out_dir
        unzip_dir.mkdir(parents=True, exist_ok=True)
        download_dir.rename(unzip_dir)
        return [convert.name]
    
branching_zipping = BranchPythonOperator(
    task_id='branching-unzipping',
    provide_context=True,
    python_callable=branching_zipping,
    dag=dag)


def branching_sending(**kwargs):
    run_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs['dag_run'].run_id
    if [p for p in run_dir.rglob('seg_info.json')]:
        return [convert_seg.name, dcm_send_img.name]
    else:
        return [dcm_send_img.name]
    
branching_sending = BranchPythonOperator(
    task_id='branching-sending',
    provide_context=True,
    python_callable=branching_sending,
    dag=dag)

def branching_cleaning_minio(**kwargs):
    conf = kwargs['dag_run'].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_minio.name]
    else:
        return [clean.name]

branching_cleaning_minio = BranchPythonOperator(
    task_id='branching-cleaning-minio',
    provide_context=True,
    trigger_rule="none_failed_min_one_success",
    python_callable=branching_cleaning_minio,
    dag=dag)


get_object_from_minio >> branching_zipping
branching_zipping >> unzip_files >> convert
branching_zipping >> convert
convert >> branching_sending
branching_sending >> convert_seg >> dcm_send_seg >> branching_cleaning_minio
branching_sending >> dcm_send_img >> branching_cleaning_minio
branching_cleaning_minio >> remove_object_from_minio >> clean
branching_cleaning_minio >> clean