from airflow.utils.dates import days_ago
from datetime import timedelta, datetime
from airflow.models import DAG
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from node_metrics.LocalGetMetricsOperator import LocalGetMetricsOperator
from node_metrics.LocalAggregateMetricsOperator import LocalAggregateMetricsOperator
from airflow.utils.trigger_rule import TriggerRule
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.blueprints.kaapana_global_variables import (
    KAAPANA_BUILD_VERSION,
    INSTANCE_NAME,
    SERVICES_NAMESPACE,
)
from kaapana.operators.DcmSendOperator import DcmSendOperator

max_active_runs = 5
args = {
    "ui_visible": False,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}

dag = DAG(
    dag_id="metrics-collect-node",
    default_args=args,
    concurrency=4,
    max_active_runs=1,
    schedule_interval="@hourly",
)

get_host_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="windows-server",
    metrics_endpoint="http://kaapana-02:9000/metrics",
    timeout=20,
)
get_jip_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="jip",
    metrics_endpoint=f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/monitoring/metrics/scrape",
    verify_ssl=False,
)
get_satori_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="satori",
    metrics_endpoint=f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/monitoring/metrics/scrape",
    verify_ssl=False,
)
get_imfusion_metrics = LocalGetMetricsOperator(
    dag=dag,
    component_id="imfusion",
    metrics_endpoint=f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000/monitoring/metrics/scrape",
    verify_ssl=False,
)

aggregate_metrics = LocalAggregateMetricsOperator(
    dag=dag,
    metrics_operators=[get_host_metrics, get_satori_metrics, get_jip_metrics, get_imfusion_metrics],
    instance_name=INSTANCE_NAME,
    version=KAAPANA_BUILD_VERSION,
    trigger_rule=TriggerRule.ALL_DONE,
)
txt2dcm = Bin2DcmOperator(
    dag=dag,
    name="metrics2dicom",
    patient_name="node-metrics",
    instance_name=INSTANCE_NAME,
    manufacturer="Kaapana",
    manufacturer_model="node-metrics",
    version=KAAPANA_BUILD_VERSION,
    study_id="node-metrics",
    study_uid=None,
    protocol_name=None,
    study_description=None,
    series_description=f"Node metrics from {INSTANCE_NAME} | {datetime.now().astimezone().replace(microsecond=0).isoformat()}",
    size_limit=10,
    input_operator=aggregate_metrics,
    file_extensions="*.txt",
)

dcm_send_int = DcmSendOperator(
    dag=dag,
    level="batch",
    pacs_host=f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc",
    pacs_port="11112",
    ae_title="node-metrics",
    input_operator=txt2dcm,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_host_metrics >> aggregate_metrics
get_satori_metrics >> aggregate_metrics
get_imfusion_metrics >> aggregate_metrics
get_jip_metrics >> aggregate_metrics
aggregate_metrics >> txt2dcm >> dcm_send_int >> clean
