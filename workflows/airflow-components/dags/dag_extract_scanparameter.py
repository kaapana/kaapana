from datetime import datetime
from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin

from extract_scanparameter.ExtractScanparameterOperator import ExtractScanparameterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

timestamp = datetime.now().strftime("%d.%m.%Y %H:%M")

# ui_forms = {
#     "workflow_form": {
#         "type": "object",
#         "properties": {
#             "single_execution": {
#                 "title": "single execution",
#                 "description": "Should each series be processed separately?",
#                 "type": "boolean",
#                 "default": False,
#                 "readOnly": False,
#             }
#         }
#     }
# }

args = {
    #'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='extract-scanparameter',
    default_args=args,
    #concurrency=gpu_count,
    concurrency=30,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)
extract_scanparameter = ExtractScanparameterOperator(dag=dag)
put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[extract_scanparameter], file_white_tuples=('.json', '*'))
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> extract_scanparameter >> put_to_minio >> clean