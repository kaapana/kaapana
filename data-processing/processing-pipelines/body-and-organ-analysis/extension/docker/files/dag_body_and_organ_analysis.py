from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator


from body_and_organ_analysis.BodyAndOrganAnalysisOperator import BodyAndOrganAnalysisOperator

max_active_runs = 5

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
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
    dag_id="body-and-organ-analysis",
    default_args=args,
    concurrency=10,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = GetInputOperator(dag=dag, parallel_downloads=5, check_modality=False)

dcm2nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

boa = BodyAndOrganAnalysisOperator(dag=dag, input_operator=dcm2nifti)

push_to_minio = MinioOperator(
    dag=dag, 
    none_batch_input_operators=[boa],
    whitelisted_file_extensions=[".json",".xlsx",".pdf",".nii.gz"]
)

send_dicoms = DcmSendOperator(
    dag=dag, ae_title="body-organ-analysis-results", input_operator=boa, level="batch"
)


clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> dcm2nifti >> boa >> [push_to_minio, send_dicoms] >> clean
