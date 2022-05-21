from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from radiomics.RadiomicsOperator import RadiomicsOperator
log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": True,
                "readOnly": False,
            },
            "input": {
                "title": "Input",
                "default": "SEG",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
            "parameters": {
                "title": "Parameter",
                "default": "-fo 1 -cooc 1",
                "description": "Parameter for MitkCLGlobalImageFeatures.",
                "type": "string",
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
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='radiomics-dcmseg',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
dcmseg2nrrd = DcmSeg2ItkOperator(dag=dag, input_operator=get_input)
get_dicom = LocalGetRefSeriesOperator(dag=dag, input_operator=get_input)
dcm2nrrd = DcmConverterOperator(dag=dag, input_operator=get_dicom, output_format='nrrd')
radiomics = RadiomicsOperator(dag=dag, mask_operator=dcmseg2nrrd, input_operator=dcm2nrrd)

put_radiomics_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[radiomics], file_white_tuples=('.xml'))
clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcmseg2nrrd >> radiomics 
get_input >> get_dicom >> dcm2nrrd >> radiomics >> put_radiomics_to_minio >> clean
