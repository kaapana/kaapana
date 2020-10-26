from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG


from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from example.ExtractStudyIdOperator import ExtractStudyIdOperator
from example.PoolJsonsOperator import PoolJsonsOperator

log = LoggingMixin().log

args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='example-dcm-extract-multiple-study-ids',
    default_args=args,
    schedule_interval=None
    )


get_input = LocalGetInputDataOperator(dag=dag)
extract_one = ExtractStudyIdOperator(dag=dag, parallel_id='one')
extract_two = ExtractStudyIdOperator(dag=dag, parallel_id='two')
pool_jsons_one = PoolJsonsOperator(dag=dag, input_operator=extract_one)
pool_jsons_two = PoolJsonsOperator(dag=dag, input_operator=extract_two)
put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[pool_jsons_one, pool_jsons_two])
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> extract_one >> pool_jsons_one >> put_to_minio
get_input >> extract_two >> pool_jsons_two >> put_to_minio
put_to_minio >> clean

