from datetime import timedelta

from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from example.CustomNotifyOperator import CustomNotifyOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.NotifyOperator import NotifyOperator

log = LoggingMixin().log

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
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(dag_id="example-notify", default_args=args, schedule_interval=None)


get_input = GetInputOperator(dag=dag)
custom_notify = CustomNotifyOperator(dag=dag, input_operator=get_input)
notify = NotifyOperator(
    dag=dag,
    topic="nnUnet",
    title="Training finished",
    description="<p>The <strong>nnU-Net</strong> training has successfully completed.</p>",
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> notify >> custom_notify >> clean
