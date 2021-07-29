from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator

from bodypartregression.BprOperator import BprOperator

max_active_runs = 5

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "stringify_json": {
                "title": "Stringify JSON?",
                "description": "Should all nested elements be strigified?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
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
    dag_id='bodypart-regression',
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    parallel_downloads=5,
    check_modality=True
)

dcm2nifti = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format='nii.gz'
)

bodypartregression = BprOperator(
    dag=dag,
    stringify_json=True,
    input_operator=dcm2nifti
)

push_json = LocalJson2MetaOperator(
    dag=dag,
    dicom_operator=get_input,
    json_operator=bodypartregression
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2nifti >> bodypartregression >> push_json >> clean
