from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.blueprints.kaapana_global_variables import KAAPANA_BUILD_VERSION
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.GetRefSeriesOperator import GetRefSeriesOperator
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from mitk_flow.LocalBranchGetReferenceSeries import LocalBranchGetReferenceSeries
from mitk_flow.LocalMiktInputOperator import LocalMiktInputOperator

log = LoggingMixin().log

dag_info = {
    "ui_visible": True,
}

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="mitk-flow",
    default_args=args,
    concurrency=10,
    max_active_runs=5,
    schedule_interval=None,
)


get_input = GetInputOperator(dag=dag)
branch_get_ref_series = LocalBranchGetReferenceSeries(dag=dag, input_operator=get_input)
get_ref_series = GetRefSeriesOperator(
    dag=dag, input_operator=branch_get_ref_series, skip_empty_ref_dir=True
)
mitk = LocalMiktInputOperator(
    dag=dag,
    input_operator=get_input,
    operator_out_dir="mitk-results",
    trigger_rule="none_failed_or_skipped",
)
launch_app = KaapanaApplicationOperator(
    dag=dag,
    name="application-mitk-flow",
    input_operator=get_input,
    chart_name="mitk-flow-chart",
    version=KAAPANA_BUILD_VERSION,
)

send_dicom = DcmSendOperator(dag=dag, ae_title="MITK-flow", input_operator=mitk)
clean = LocalWorkflowCleanerOperator(dag=dag)

get_input >> branch_get_ref_series >> [get_ref_series, mitk]
get_ref_series >> mitk
mitk >> launch_app >> send_dicom >> clean
