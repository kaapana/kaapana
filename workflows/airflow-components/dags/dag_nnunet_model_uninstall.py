from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.getTasks import get_tasks

available_pretrained_task_names, installed_tasks, all_selectable_tasks = get_tasks()

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "Installed nnUnet Tasks",
                "description": "Select one of the installed tasks.",
                "type": "string",
                "enum": sorted(list(installed_tasks.keys())),
                "required": True
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
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-model-uninstall',
    default_args=args,
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None
)

delete_model = GetTaskModelOperator(
    dag=dag,
    name="uninstall-nnunet-task",
    mode="uninstall"
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True
)

delete_model >> clean 
