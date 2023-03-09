from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG

from node_metrics.LocalGetMetricsOperator import LocalGetMetricsOperator
from node_metrics.LocalPushToPromOperator import LocalPushToPromOperator
from node_metrics.LocalAggregateMetricsOperator import LocalAggregateMetricsOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

max_active_runs = 5

args = {
    "ui_visible": False,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="get-node-metrics",
    default_args=args,
    concurrency=4,
    max_active_runs=1,
    schedule_interval=None,
)

get_host_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="windows-server",
    metrics_endpoint="http://grafana.services.svc:3000/metrics",
)
get_satori_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="jip",
    metrics_endpoint="https://oauth2-proxy-service.admin.svc:8443/oauth2/metrics",
    verify_ssl=False,
)
get_jip_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="satori",
    metrics_endpoint="http://prometheus-service.services.svc:9090/prometheus/metrics",
)
aggregate_metrics = LocalAggregateMetricsOperator(
    dag=dag, metrics_operators=[get_host_metrics, get_satori_metrics, get_jip_metrics]
)
push_metrics = LocalPushToPromOperator(dag=dag, input_operator=aggregate_metrics)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_host_metrics >> aggregate_metrics
get_satori_metrics >> aggregate_metrics
get_jip_metrics >> aggregate_metrics

aggregate_metrics >> push_metrics >> clean
