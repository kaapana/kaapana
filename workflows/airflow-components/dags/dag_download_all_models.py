from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='get-all-nnUnet-models',
    default_args=args,
    schedule_interval=None
)

clean = LocalWorkflowCleanerOperator(dag=dag, trigger_rule="all_done")
get_task_model = GetTaskModelOperator(dag=dag, task_id="all")
get_task_model >> clean
