from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from airflow.operators.python_operator import PythonOperator

from kaapana.operators.first import first_call
from kaapana.operators.test import test_call

log = LoggingMixin().log

from airflow.models import Variable

# Operator
from airflow.operators.bash_operator import BashOperator


from datetime import datetime, timedelta

script_dir = Variable.get('fets_scripts_path')  # where my Python scripts live


default_args = {
    'depends_on_past': False,
    'start_date': datetime(2022, 3, 20, 00, 00),
    'retries': 1,
    'retry_delay': timedelta(minutes=10),
    'catchup': False
}

# Instantiate a DAG my_dag that runs every day
# DAG objects contain tasks
# Time is in UTC!!!
my_dag = DAG(dag_id='san_test_dag_wrapper',
             default_args=default_args,
             schedule_interval='0 0 1 * *', )  # 8:30AM EST

# Hack to stop backfilling upstream tasks


task_1 = PythonOperator(
    task_id='task_1_print_fets',
    python_callable=first_call,
    dag=my_dag
)

# Instantiate tasks
task_2 = PythonOperator(
    task_id='task_2_print_fets',
    python_callable=test_call,
    dag=my_dag
)



# set task relationship
task_1 >> task_2