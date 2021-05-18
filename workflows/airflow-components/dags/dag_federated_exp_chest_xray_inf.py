from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin

from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

#from kaapana.operators.LocalMinioOperator import LocalMinioOperator
# --> TODO: needs option to overwrite name

from federated_training.experiments.ExperimentChestXrayOperator import ExperimentChestXrayOperator


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='federated-experiment-chest-xray-inference',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
)

get_test_data = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-data',
    action='get',
    bucket_name='federated-exp-chest-xray',
    action_operator_dirs=['data'],
    operator_out_dir='data'
)

unzip_data = LocalUnzipFileOperator(dag=dag, input_operator=get_test_data)

get_model = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-model',
    action='get',
    bucket_name='federated-exp-chest-xray',
    action_operator_dirs=['model'],
    operator_out_dir='model'
)

inference = ExperimentChestXrayOperator(
    dag=dag,
    name='inference',
    input_operator=unzip_data,
    inference=True,
    ram_mem_mb=2000
)

cleanup = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

[get_test_data >> unzip_data, get_model] >> inference >> cleanup