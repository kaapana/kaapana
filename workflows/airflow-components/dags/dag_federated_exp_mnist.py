from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin

from kaapana.operatorsLocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from federated_training.ExpSchedulerOperatorMNIST import ExpSchedulerOperatorMNIST


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='federated-experiment-mnist',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
)

get_data_from_minio = LocalMinioOperator(
    dag=dag,
    action='get',
    bucket_name='federated-exp-mnist',
    action_operator_dirs=['data'],
    operator_out_dir='data'
)

unzip_data = LocalUnzipFileOperator(
    dag=dag,
    operator_in_dir='data'
)

training_workflow = ExpSchedulerOperatorMNIST(
    dag=dag,
    input_operator=unzip_data,
    scheduler='10.128.129.76',
    procedure='avg',
    participants='["", "", ""]' #add IPs - WARNING: "quotation marks" are important! Otherwise cannot be parsed as envs!
)

cleanup = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_data_from_minio >> unzip_data >> training_workflow >> cleanup