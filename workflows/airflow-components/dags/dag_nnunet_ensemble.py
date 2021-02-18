from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.getTasks import get_tasks
from kaapana.operators.ResampleOperator import ResampleOperator
from nnunet.LocalSegCheckOperator import LocalSegCheckOperator
# from nnunet.GetContainerModelOperator import GetContainerModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input Modality",
                "default": "OT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
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
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='nnunet-ensemble',
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

extract_model = GetTaskModelOperator(
    dag=dag,
    name="install-model-zip",
    input_operator=dcm2bin,
    operator_out_dir="model-exports",
    mode="install_zip"
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)
get_input >> dcm2bin >> extract_model >> clean
