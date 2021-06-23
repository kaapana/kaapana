from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from RacoonUkfSeg.PresegmentationOperator import PresegmentationOperator
from datetime import timedelta

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
    'owner': 'UKF',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='racoon-ukf-presegmentation',
    default_args=args,
    concurrency=50,
    max_active_runs=30,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    operator_out_dir="initial-input"
)
nnunet_predict = PresegmentationOperator(
    dag=dag,
    input_operator=get_input
)

dcmseg_send = DcmSendOperator(dag=dag, input_operator=nnunet_predict)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

get_input >> nnunet_predict  >> dcmseg_send >>  clean