from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from nnunet.NnUnetModelOperator import NnUnetModelOperator

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.GetInputOperator import GetInputOperator

ui_forms = {
    "documentation_form": {
        "path": "/user_guide/extensions.html#nnunet-install-model",
    },
    "data_form": {
        "type": "object",
        "properties": {
            "dataset_name": {
                "type": "string",
                "title": "Dataset with models to install (size)",
                "oneOf": [],
                "required": True,
            },
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input",
                "default": "OT",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
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
    dag_id="nnunet-install-model",
    default_args=args,
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None,
)

get_input = GetInputOperator(
    dag=dag, name="get-models", check_modality=True, parallel_downloads=5
)

dcm2bin = Bin2DcmOperator(
    dag=dag, input_operator=get_input, name="extract-binary", file_extensions="*.dcm"
)

model_management = NnUnetModelOperator(
    dag=dag, name="install-model", input_operator=dcm2bin, action="install"
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule="none_failed",
)

get_input >> dcm2bin >> model_management >> clean
