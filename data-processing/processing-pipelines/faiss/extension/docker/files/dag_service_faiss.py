from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from SendToFaissOperator import SendToFaissOperator


max_active_runs = 5

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": True,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=60),
}


dag = DAG(
    dag_id="service-faiss",
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None,
    tags=["service"],
)

get_input = LocalGetInputDataOperator(
    dag=dag, parallel_downloads=5, check_modality=True
)

send_to_faiss = SendToFaissOperator(dag=dag, input_operator=get_input)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_input >> send_to_faiss >> clean
