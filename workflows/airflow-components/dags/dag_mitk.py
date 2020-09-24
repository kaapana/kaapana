from airflow.models import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from datetime import datetime

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from mitk_userflow.RunMitk import RunMitk


dag_info = {
    "visible": True,
}

args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 0,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=30000),
}

dag = DAG(
    dag_id='mitk',
    default_args=args,
    schedule_interval=None)

get_input = LocalGetInputDataOperator(dag=dag)
run_mitk = RunMitk(dag=dag)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> run_mitk >> clean