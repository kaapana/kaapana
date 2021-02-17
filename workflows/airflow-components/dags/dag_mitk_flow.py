from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from datetime import timedelta
from airflow.models import DAG
from mitk_flow.MitkInputOperator import MitkInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator


from datetime import datetime

import os

log = LoggingMixin().log

dag_info = {
    "ui_visible": True,
}

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='mitk-flow',
    default_args=args,
    concurrency=10,
    max_active_runs=5,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
mitk_input = MitkInputOperator(dag=dag, input_operator=get_input)

launch_app = KaapanaApplicationOperator(dag=dag,
                                        name="application-mitk-flow",
                                        input_operator=mitk_input,
                                        chart_name='mitk-flow-chart',
                                        version='2021.02-vdev')
send_dicom = DcmSendOperator(dag=dag, input_operator=launch_app, ae_title="MITK-flow")
clean = LocalWorkflowCleanerOperator(dag=dag)


get_input >> mitk_input >> launch_app >> send_dicom >> clean
