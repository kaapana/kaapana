from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.trigger_rule import TriggerRule

from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from openmined.RunNodeOperator import RunNodeOperator
from openmined.ProvideDataOperator import OpenminedProvideDataOperator


log = LoggingMixin().log

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='openmined-provide-data',
    default_args=args,
    schedule_interval=None,
    concurrency=10,
    max_active_runs=5
    )

get_object_from_minio = LocalMinioOperator(
    dag=dag,
    action='get',
    bucket_name='openmined-data',
    action_operator_dirs=['MNIST-split'],
    operator_out_dir='MNIST-split'
    )

unzip_files = LocalUnzipFileOperator(
    dag=dag,
    operator_in_dir='MNIST-split'
    )

run_node = RunNodeOperator(
    dag=dag, 
    operator_in_dir='./',
    release_name='openmined-node',
    global_id=None,     #i.e. 'co',
    hostname=None,      #i.e. '10.128.129.6',
    port='5000',
    grid_network=None   #i.e. '10.128.129.76:7000'
    )

data2node = OpenminedProvideDataOperator(
    dag=dag,
    input_operator=unzip_files,
    hostname=None,      #i.e. '10.128.129.6,
    port='5000',
    lifespan='15',
    dataset='mnist',
    exp_tag="#no-tag-given"
    )

clean = LocalWorkflowCleanerOperator(dag=dag)

get_object_from_minio >> unzip_files >> [run_node, data2node] >> clean