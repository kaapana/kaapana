from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.GetTaskModelOperator import GetTaskModelOperator

dag_info = {
    "visible": False,
}

args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='get-all-nnUnet-models',
    default_args=args,
    schedule_interval=None
)

get_task_model = GetTaskModelOperator(dag=dag,task_id="all")
