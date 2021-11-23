from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG

ae_title = "NONE"

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "aetitle": {
                "title": "Receiver AE-title/Dataset name",
                "description": "Specify the port of the DICOM receiver.",
                "type": "string",
                "default": ae_title,
                "required": True
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            }
        }
    }
}

args = {
    'ui_visible': True,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='tag-dataset',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag)

dcm_send = DcmSendOperator(
    dag=dag,
    input_operator=get_input,
    ae_title=ae_title
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm_send >> clean