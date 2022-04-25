from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from airflow.operators.python_operator import PythonOperator

from tfda_execution_orchestrator.LocalFeTSSubmissions import LocalFeTSSubmissions
from tfda_execution_orchestrator.LocalFeTSTest import LocalFeTSTest

log = LoggingMixin().log

from airflow.models import Variable

# Operator
from airflow.operators.bash_operator import BashOperator


from datetime import datetime, timedelta

# script_dir = Variable.get('fets_scripts_path')  # where my Python scripts live


args = {
    'depends_on_past': False,
    'start_date': datetime(2022, 4, 26, 00, 00),
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    'catchup': False
}

# Instantiate a DAG my_dag that runs every day
# DAG objects contain tasks
# Time is in UTC!!!
dag = DAG(dag_id='dag-tfda-fets-task',
             default_args=default_args,
             schedule_interval='0 0 1 * *', )  # 8:30AM EST

# Hack to stop backfilling upstream tasks

evaluate_submissions = LocalFeTSSubmissions(dag=dag)
test = LocalFeTSTest(dag=dag)

# set task relationship
evaluate_submissions >> test