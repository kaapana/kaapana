from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.NnUnetModelOperator import NnUnetModelOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from nnunet.getTasks import get_tasks

available_pretrained_task_names, installed_tasks, all_selectable_tasks = get_tasks()

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "uninstall_task": {
                "title": "Unisntall nnUnet Model",
                "description": "Select one of the installed models to uninstall.",
                "type": "string",
                "default": "",
                "enum": sorted(list(installed_tasks.keys())),
                "required": False
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

get_input = LocalGetInputDataOperator(
    dag=dag,
    check_modality=True,
    parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag,
    input_operator=get_input,
    name="extract-binary",
    file_extensions="*.dcm"
)

model_management = NnUnetModelOperator(
    dag=dag,
    name="model-management",
    input_operator=dcm2bin,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

get_input >> dcm2bin >> model_management >> clean
