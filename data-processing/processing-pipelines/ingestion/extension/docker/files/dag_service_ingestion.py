from datetime import timedelta
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule

from ingestion.LocalIngestionOperator import LocalIngestionOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator


args = {
    "ui_visible": False,
    "owner": "system",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="service-ingestion",
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=["service"],
)

get_input = LocalGetInputDataOperator(dag=dag, delete_input_on_success=True)
ingestion = LocalIngestionOperator(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)

get_input >> ingestion >> clean
