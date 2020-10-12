from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from datetime import timedelta

from airflow.models import DAG

from mitk_userflow.MitkInputOperator import MitkInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.KaapanaApplicationBaseOperator import KaapanaApplicationBaseOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator


from datetime import datetime

import os

log = LoggingMixin().log

dag_info = {
    "ui_visible": True,
}

args = {
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='mitk-flow',
    default_args=args,
    schedule_interval=None)

get_input = LocalGetInputDataOperator(dag=dag)
mitk_input = MitkInputOperator(dag=dag)

launch_app = KaapanaApplicationBaseOperator(dag=dag, name="application-mitk-flow", chart_name='mitk-flow-chart', version='0.1-vdev')
send_dicom = DcmSendOperator(dag=dag, input_operator=launch_app)
clean = LocalWorkflowCleanerOperator(dag=dag)



get_input  >> mitk_input >> launch_app >> send_dicom >> clean