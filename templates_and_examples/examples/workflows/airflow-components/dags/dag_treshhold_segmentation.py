from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from treshhold_segmentation.OtsuThresholdOperater import OtsuThresholdOperater

log = LoggingMixin().log

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
            }
        }
    }
}

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='treshhold-segmentation',
    default_args=args,
    schedule_interval=None
    )


get_dicom = LocalGetInputDataOperator(dag=dag)
nrrd_file = DcmConverterOperator(dag=dag, input_operator=get_dicom, output_format='nrrd')
segmentation = OtsuThresholdOperater(dag=dag, input_operator=nrrd_file)
dicom_seg = Itk2DcmSegOperator(dag=dag, input_operator=get_dicom, segmentation_operator=segmentation, single_label_seg_info="Entire body")
dcmseg_send = DcmSendOperator(dag=dag, input_operator=dicom_seg)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_dicom >> nrrd_file >> segmentation >> dicom_seg >> dcmseg_send >> clean
