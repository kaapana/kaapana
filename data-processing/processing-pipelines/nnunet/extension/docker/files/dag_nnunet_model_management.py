from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.NnUnetModelOperator import NnUnetModelOperator
from nnunet.LocalModelGetInputDataOperator import LocalModelGetInputDataOperator
# from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from nnunet.getTasks import get_tasks, get_available_protocol_names

available_pretrained_task_names, installed_tasks, all_selectable_tasks = get_tasks()

available_protocol_names  = get_available_protocol_names()
installed_protocol_names = list(installed_tasks.keys())
ui_forms = {
    "data_form": {
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            # tasks is used in multiple operator, do not change it to install_tasks...
            "tasks": {
                "title": "Install tasks",
                "description": "Select available tasks",
                "type": "array",
                "items": {"type": "string", "enum": sorted([t for t in available_protocol_names if t not in installed_protocol_names])}
            },
            "uninstall_tasks": {
                "title": "Uninstall tasks",
                "description": "Select one of the installed models to uninstall.",
                "type": "array",
                "items": {"type": "string", "enum": sorted(installed_protocol_names)},
            }
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
    dag_id="nnunet-model-management",
    default_args=args,
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = LocalModelGetInputDataOperator(
    dag=dag, name="get-models", check_modality=True, parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag, input_operator=get_input, name="extract-binary", file_extensions="*.dcm"
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
