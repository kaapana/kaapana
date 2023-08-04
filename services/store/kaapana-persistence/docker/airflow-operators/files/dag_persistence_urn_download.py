from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from persistence.LocalGetUrnOperator import LocalGetUrnOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "urns": {
                "title": "URNs",
                "description": "Specify a , separated list of uns to download",
                "type": "string",
                "default": "",
                "required": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
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
    "retry_delay": timedelta(seconds=30),
}


dag = DAG(
    dag_id="persistence-test-urn-input",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)

get_input = LocalGetUrnOperator(dag=dag)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

get_input >> clean
