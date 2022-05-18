from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalAutoTriggerOperator import LocalAutoTriggerOperator
from kaapana.operators.LocalMultiAETitleOperator import LocalMultiAETitleOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from datetime import timedelta

args = {
    'ui_visible': False,
    'owner': 'system',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='service-process-incoming-dcm',
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=['service']
)

get_input = LocalGetInputDataOperator(dag=dag)

dcm_check = LocalMultiAETitleOperator(
    dag=dag,
    input_operator=get_input
)

dcm_send = LocalDicomSendOperator(
   dag=dag,
   input_operator=dcm_check,
   pacs_host='dcm4chee-service.store.svc',
   pacs_port=11115,
   ae_title='KAAPANA',
   check_arrival=True
)

auto_trigger_operator = LocalAutoTriggerOperator(
    dag=dag,
    input_operator=dcm_check
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_input >> dcm_check >> dcm_send >> auto_trigger_operator >> clean
