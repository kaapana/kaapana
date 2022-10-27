from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from otsus_method.OtsusMethodOperator import OtsusMethodOperator


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
    dag_id='otsus-method',
    default_args=args,
    schedule_interval=None
    )



get_input = LocalGetInputDataOperator(dag=dag)
convert = DcmConverterOperator(dag=dag, input_operator=get_input)
otsus_method = OtsusMethodOperator(dag=dag, input_operator=convert)
seg_to_dcm = Itk2DcmSegOperator(dag=dag, segmentation_operator=otsus_method,
                                single_label_seg_info="abdomen",
                                input_operator=get_input,
                                series_description="Otsu's method")
dcm_send = DcmSendOperator(dag=dag, input_operator=seg_to_dcm)
clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> convert >> otsus_method >> seg_to_dcm >> dcm_send >> clean