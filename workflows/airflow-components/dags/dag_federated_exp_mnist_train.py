from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin

from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
#from kaapana.operators.LocalMinioOperator import LocalMinioOperator
# --> TODO: needs option to overwrite its name, so two minio-action-get can be applied

from federated_training.experiments.TrainingMNISTOperator import TrainingMNISTOperator


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='federated-exp-mnist-training',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
)

get_model_from_minio = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-model',
    action='get',
    bucket_name='federated-exp-mnist',
    action_operator_dirs=['model', 'logs']
    )

get_data_from_minio = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-data',
    action='get',
    bucket_name='federated-exp-mnist',
    action_operator_dirs=['data'],
    operator_out_dir='data'
    )

unzip_data = LocalUnzipFileOperator(
    dag=dag,
    operator_in_dir='data'
    )

train_model = TrainingMNISTOperator(
    dag=dag,
    input_operator=unzip_data,
    host_ip=None,
    epochs=1,
    batch_size=32,
    use_cuda=True,
    validation=True
    )

pass_on_model = LocalMinioOperator(
    dag=dag,action='put',
    bucket_name='federated-exp-mnist',
    action_operator_dirs=['cache', 'logs'],
    operator_out_dir='',
    file_white_tuples=('','.pt'),
    zip_files=False
    )

cleanup = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
 
[get_model_from_minio, get_data_from_minio >> unzip_data] >> train_model >> pass_on_model >> cleanup