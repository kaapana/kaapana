from kaapana.operators.LocalCtpQuarantineCheckOperator import LocalCtpQuarantineCheckOperator
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
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='process-incoming-dcm-local',
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=['service']
)

get_input = LocalGetInputDataOperator(dag=dag)

dcm_send = LocalDicomSendOperator(
    dag=dag,
    input_operator=get_input,
    pacs_host='dcm4chee-service.store.svc',
    pacs_port=11115,
    ae_title='KAAPANA',
    check_arrival=True
)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_input >>  dcm_send >> clean
