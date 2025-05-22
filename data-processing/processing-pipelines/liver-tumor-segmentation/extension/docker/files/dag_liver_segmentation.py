from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from liver_segmentation.LiverSegmentationOperator import LiverSgmentationOperator

log = LoggingMixin().log

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/system/airflow.html#mri-liver-tumor-segmentation-workflow",
    },
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
        },
    },
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="mri-liver-tumor-segmentation-workflow",
    default_args=args,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input, output_format="nii.gz")
liver_segmentation = LiverSgmentationOperator(dag=dag, input_operator=convert)
seg_to_dcm = Itk2DcmSegOperator(
    dag=dag,
    segmentation_operator=liver_segmentation,
    input_operator=get_input,
    multi_label_seg_name='monaiseg',
    input_type='multi_label_seg',
    multi_label_seg_info_json='info.json',
    series_description="mri liver tumor segmentation",
)
dcm_send = DcmSendOperator(dag=dag, ae_title='stunet-predict-results', input_operator=seg_to_dcm)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> convert >> liver_segmentation >> seg_to_dcm >> dcm_send >> clean

