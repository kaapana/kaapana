from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.operators.dummy_operator import DummyOperator
from m2olie.LocalCallbackfunction import LocalCallbackfunction
from mitk_flow.LocalMiktInputOperator import LocalMiktInputOperator
from kaapana.operators.KaapanaApplicationOperator import KaapanaApplicationOperator
from kaapana.blueprints.kaapana_global_variables import KAAPANA_BUILD_VERSION

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
            },
            "task_label": {
                "title": "Task Label",
                "description": "The M2olie Prometheus task label",
                "type": "string",
                "readOnly": False,
            },
            "process_instance_label": {
                "title": "Process Instance Label",
                "description": "The M2olie Prometheus process instance label",
                "type": "string",
                "readOnly": False,
            },
            "callback_instance_ip": {
                "title": "Callback Instance IP",
                "description": "The M2olie Prometheus callback ip.",
                "type": "string",
                "readOnly": False,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_federated": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="image_segmentation",
    default_args=args,
    concurrency=10,
    max_active_runs=1,
    schedule_interval=None,
    tags=["m2olie"],
)

get_input = LocalGetInputDataOperator(dag=dag)
segmentation = DummyOperator(dag=dag, task_id="segmentation-dummy")
mitk_input = LocalMiktInputOperator(
    dag=dag, input_operator=get_input, operator_out_dir="mitk-results"
)
launch_app = KaapanaApplicationOperator(
    dag=dag,
    name="application-segmentation-flow",
    input_operator=get_input,
    chart_name="mitk-flow-chart",
    version=KAAPANA_BUILD_VERSION,
)
m2olie_callback_funktion = LocalCallbackfunction(dag=dag, input_operator=get_input)
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> mitk_input >> segmentation >> launch_app >> clean
segmentation >> m2olie_callback_funktion >> clean
