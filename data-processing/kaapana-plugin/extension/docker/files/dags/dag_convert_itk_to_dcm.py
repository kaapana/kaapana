from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.Itk2DcmOperator import Itk2DcmOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator

# from example.ExtractStudyIdOperator import ExtractStudyIdOperator
# from example.ConversionOperator import ConvertItk2DcmOperator

from pathlib import Path

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
            "data_dir":{
                "title": "Data directory",
                "description": "Directory containing the dataset.",
                "type": "string",
                "default": "BMC"
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
    dag_id='dag-convert-nifti-2-dcm',
    default_args=args,
    schedule_interval=None
    )



bucket_name='uploads'
upload_folder_tree = 'itk'

get_data_from_minio = LocalMinioOperator(
    action='get',
    dag=dag,
    bucket_name=bucket_name,
    action_operator_dirs=[upload_folder_tree],
    operator_out_dir=upload_folder_tree,
    split_level=1)

convert = Itk2DcmOperator(
    dag=dag, 
    name="convert-itk2dcm", 
    # dev_server='code-server',
    input_operator=get_data_from_minio) 

# send_dcm_to_pacs = LocalDicomSendOperator(
#     dag=dag,
#     input_operator = convert
# )

convert_seg = Itk2DcmSegOperator(
    dag=dag,
    # config_file=Path(convert.operator_out_dir)/'segmentations/seg_args.json',
    name="convert-segmentation", 
    segmentation_in_dir=Path(convert.operator_out_dir)/'segmentations', 
    dev_server='code-server',
    operator_in_dir=Path(convert.operator_out_dir)/'dicoms')

dcm_send_seg = DcmSendOperator(
    name="dcm-send-seg",
    dag=dag,
    input_operator=convert_seg
)

dcm_send_img = DcmSendOperator(
    name="dcm-send-img",
    dag=dag,
    operator_in_dir=Path(convert.operator_out_dir)/'dicoms'
)

# send_segs_to_pacs = LocalDicomSendOperator(
#     dag=dag,
#     input_operator = convert_seg
# )

# put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[convert])
# clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_data_from_minio >> convert >> convert_seg >> dcm_send_img >> dcm_send_seg# >> put_to_minio # >> clean