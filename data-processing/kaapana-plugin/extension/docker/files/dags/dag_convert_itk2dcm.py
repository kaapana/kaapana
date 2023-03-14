from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator

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
itk_objects = [obj.object_name for obj in objects if obj.object_name != "itk/readme.txt"]

ui_forms = {
    "data_form": {
        "type": "object",
        "properties": {
            "bucket_name": {
                "title": "Bucket name",
                "description": "Bucket name from MinIO",
                "type": "string",
                "default": "uploads",
                "readOnly": True
            },
            "action_files":  {
                "title": "ZIP files from bucket",
                "description": "Relative paths to zip file in Bucket",
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": itk_objects
                },
                "required": True,
                "readOnly": False
            },
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "modality":{
                "title": "modality",
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
    operator_out_dir="itk",
    split_level=1)

unzip_files = ZipUnzipOperator(
    dag=dag,
    input_operator=get_object_from_minio,
    batch_level=True,
    mode="unzip"
)
    
convert = Itk2DcmOperator(
    dag=dag, 
    name="convert-itk2dcm", 
    # dev_server='code-server',
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

clean = LocalWorkflowCleanerOperator(dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=False)

def branch_func(**kwargs):
    run_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs['dag_run'].run_id
    if [p for p in run_dir.rglob('seg_info.json')]:
        return [convert_seg.name, dcm_send_img.name]
    else:
        return [dcm_send_img.name]

branch_op = BranchPythonOperator(
    task_id='branching',
    provide_context=True,
    python_callable=branch_func,
    dag=dag)

get_object_from_minio >> unzip_files >> convert >> branch_op
branch_op >> convert_seg >> dcm_send_seg >> clean
branch_op >> dcm_send_img >> clean
