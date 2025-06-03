from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.NnUnetModelOperator import NnUnetModelOperator

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.getTasks import get_tasks

available_pretrained_task_names, installed_tasks, all_selectable_tasks = get_tasks()

installed_protocol_names = list(installed_tasks.keys())
ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#nnunet-uninstall-models",
    },
    "data_form": {},
    "workflow_form": {
        "type": "object",
        "properties": {
            "uninstall_tasks": {
                "title": "Uninstall tasks",
                "description": "Select one of the installed models to uninstall.",
                "type": "array",
                "items": {"type": "string", "enum": sorted(installed_protocol_names)},
            },
        },
    },
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
    dag_id="nnunet-uninstall-models",
    default_args=args,
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None,
)


model_management = NnUnetModelOperator(
    dag=dag, name="uninstall-model", action="uninstall"
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

model_management >> clean
