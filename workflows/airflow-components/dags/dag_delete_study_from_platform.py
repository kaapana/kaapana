from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime

from kaapana.operators.LocalDeleteFromElasticOperator import LocalDeleteFromElasticOperator
from kaapana.operators.LocalDeleteFromPacsOperator import LocalDeleteFromPacsOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log


args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='delete-study-from-platform',
    default_args=args,
    concurrency=30,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
delete_dcm_pacs = LocalDeleteFromPacsOperator(dag=dag, delete_complete_study=True)
delete_dcm_elastic = LocalDeleteFromElasticOperator(dag=dag, delete_complete_study=True)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> delete_dcm_pacs >> delete_dcm_elastic >> clean
