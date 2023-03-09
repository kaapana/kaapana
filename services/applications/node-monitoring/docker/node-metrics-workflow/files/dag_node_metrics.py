from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from node_metrics.LocalGetMetricsOperator import LocalGetMetricsOperator

max_active_runs = 5

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='get-node-metrics',
    default_args=args,
    concurrency=4,
    max_active_runs=1,
    schedule_interval=None
)

get_host_metrics = LocalGetMetricsOperator(dag=dag)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_host_metrics >> clean
