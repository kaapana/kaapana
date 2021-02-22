from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalUnzipFileOperator import LocalUnzipFileOperator
from openmined.openmined.OpenminedProvideDataOperator import OpenminedProvideDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from datetime import timedelta
from airflow.models import DAG


DATASET = 'mnist' #'xray'
NODE_HOST = '10.128.129.6'
NODE_PORT = '5000'
FOLDER_DATASPLIT = 'MNIST-split' #'XRAY-split'
LIFESPAN = '15'

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

get_object_from_minio = LocalMinioOperator(dag=dag, action='get', bucket_name='openmined-data', action_operator_dirs=[FOLDER_DATASPLIT], operator_out_dir=FOLDER_DATASPLIT)
unzip_files = LocalUnzipFileOperator(dag=dag, input_operator=get_object_from_minio, operator_in_dir=FOLDER_DATASPLIT)
data2node = OpenminedProvideDataOperator(dag=dag, input_operator=unzip_files, node_host=NODE_HOST, node_port=NODE_PORT, dataset=DATASET, lifespan=LIFESPAN)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_object_from_minio >> unzip_files >> data2node >> clean