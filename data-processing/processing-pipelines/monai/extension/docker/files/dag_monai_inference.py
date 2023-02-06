import copy
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from airflow.utils.log.logging_mixin import LoggingMixin

from monai_inference.GetMONAIModelOperator import GetMONAIModelOperator
from monai_inference.MONAIModelInferenceOperator import MONAIModelInferenceOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator


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
        }
    }
}

args = {
    'ui_forms': ui_forms,
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 2,
    'retry_delay': timedelta(seconds=30),
}

dag = DAG(
    dag_id='monai_inference',
    default_args=args,
    concurrency=50,
    max_active_runs=50,
    schedule_interval=None
    )


# get_input = LocalGetInputDataOperator(
#     dag=dag,
#     parallel_downloads=5,
#     check_modality=True
# )

# dcm2nifti = DcmConverterOperator(
#     dag=dag,
#     input_operator=get_input,
#     output_format='nii.gz'
# )

get_monai_model = GetMONAIModelOperator(
    dag=dag,
    dev_server=None,    # "code-server" , None
    )

monai_inference = MONAIModelInferenceOperator(
    dag=dag,
    # input_operator=dcm2nifti,
    minio_data_input_bucket = "monai-test",
    dev_server="code-server",
    )

# dcmseg_send = DcmSendOperator(dag=dag, input_operator=monai_inference)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

# get_input >> dcm2nifti >> monai_inference >> dcmseg_send >> clean
# get_monai_model >> monai_inference
get_monai_model >> monai_inference >> clean