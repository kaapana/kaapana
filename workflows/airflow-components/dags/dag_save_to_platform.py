
from airflow.models import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from kaapana.operators.DcmWebSendOperator import DcmWebSendOperator
from kaapana.operators.LocalDagTriggerOperator import LocalDagTriggerOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator


dag_info = {
    "visible": False,
}

args = {
    'owner': 'airflow',
    'start_date': days_ago(0),
    'retries': 3,
    'dag_info': dag_info,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='save_to_platfrom',
    default_args=args,
    schedule_interval=None)


save_to_local_pacs = DcmWebSendOperator(dag=dag, task_id='save_to_local_pacs')
trigger_extract_meta = LocalDagTriggerOperator(dag=dag, trigger_dag_id='extract-metadata')
clean = LocalWorkflowCleanerOperator(dag=dag)

save_to_local_pacs >> trigger_extract_meta >> clean