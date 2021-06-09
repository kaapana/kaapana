from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.api.common.experimental import pool as pool_api

from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
#from kaapana.operators.LocalMinioOperator import LocalMinioOperator
# --> TODO: needs option to overwrite name (otherwise cant be used twice in one dag - name conflict)

from federated_training.experiments.TrainingBraTSOperator import TrainingBraTSOperator


log = LoggingMixin().log


args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='federated-exp-brats-training',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
    )

get_model_from_minio = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-model',
    action='get',
    bucket_name='federated-exp-brats',
    action_operator_dirs=['model', 'logs']
    )

get_data_from_minio = LocalMinioOperator(
    dag=dag,
    name='minio-action-get-data',
    action='get',
    bucket_name='federated-exp-brats',
    action_operator_dirs=['brats_data'],
    operator_out_dir='brats_data'
    )

unzip_data = LocalUnzipFileOperator(
    dag=dag,
    input_operator=get_data_from_minio
    )

train_model = TrainingBraTSOperator(
    dag=dag,
    input_operator=unzip_data,
    host_ip='',
    epochs=1,
    batch_size=2,
    val_interval=1,
    validation=True,
    return_best_model=False,
    verbose=False,
    )

pass_on_model = LocalMinioOperator(
    dag=dag,action='put',
    bucket_name='federated-exp-brats',
    action_operator_dirs=['cache', 'logs'],
    operator_out_dir='',
    file_white_tuples=('','.pt'),
    zip_files=False
    )

cleanup = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)
 
[get_model_from_minio, get_data_from_minio >> unzip_data] >> train_model >> pass_on_model >> cleanup