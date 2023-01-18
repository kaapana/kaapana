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

from avid_operator.AVIDBaseOperator import AVIDBaseOperator
from avid.actions.MitkFileConverter import MitkFileConverterBatchAction

from kaapana.operators.KaapanaBaseOperator import default_registry, kaapana_build_version
from avid.actions.MitkCLGlobalImageFeatures import MitkCLGlobalImageFeaturesBatchAction as RadiomicsBatchAction
#from avid.actions.MitkGIFeatureValueCollector import MitkGIFeatureValueCollectorBatchAction as CollectorBatchAction
from avid_operator.HelperAvid import PROP_BATCH_ID
from avid.linkers import KeyValueLinker

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
    'retries': 0,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='radiomics-dcmseg-new',
    default_args=args,
    schedule_interval=None,
    concurrency=30,
    max_active_runs=15
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
dcmseg2nrrd = DcmSeg2ItkOperator(dag=dag, input_operator=get_input)
#dcmseg2nrrd = AVIDBaseOperator(dag=dag, input_operator=get_input, name='avid-convert-seg',
#                        batch_action_class = MitkFileConverterBatchAction,
#                        input_alias='inputSelector',
#                        executable_url='/src/MitkFileConverter.sh',
#                        image=f"{default_registry}/mitk-fileconverter:2021-02-18-python",
#                        image_pull_secrets=["registry-secret"],
#                        actionID="MitkFileConverter")
get_dicom = LocalGetRefSeriesOperator(dag=dag, input_operator=get_input)
#dcm2nrrd = DcmConverterOperator(dag=dag, input_operator=get_dicom, output_format='nrrd')
dcm2nrrd = AVIDBaseOperator(dag=dag, input_operator=get_dicom, name='MitkFileConverter',
                        batch_action_class = MitkFileConverterBatchAction,
                        input_alias='inputSelector',
                        executable_url='/kaapanasrc/MitkFileConverter.sh',
                        image=f"{default_registry}/mitk-radiomics:{kaapana_build_version}")

radiomics = AVIDBaseOperator(dag=dag, input_operator=dcm2nrrd, additional_inputs={"maskSelector": dcmseg2nrrd}, name='avid-radiomics',
                        batch_action_class = RadiomicsBatchAction,
                        executable_url='/kaapanasrc/MitkCLGlobalImageFeatures.sh',
                        input_alias='imageSelector',
                        image=f"{default_registry}/mitk-radiomics:{kaapana_build_version}",
                        actionID= "MitkCLGlobalImageFeatures",
                        action_kwargs={"maskLinker": KeyValueLinker(PROP_BATCH_ID),
                            "cliArgs":{"cooccurence2":None,"first-order":None, "same-space":None}}) 

#collect_features = AVIDPythonOperator(dag=dag, input_operator=radiomics, name='avid-feature-collector',
#                        batch_action_class = CollectorBatchAction,
#                        input_alias='feature_selector') 


put_radiomics_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[radiomics], file_white_tuples=('.xml'))
#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)
#removing parallel execution of AVID for now, because the session file could be called at the same time..
#get_input >> dcmseg2nrrd >> radiomics 
get_input >> get_dicom >> dcmseg2nrrd  >> dcm2nrrd  >> radiomics >> put_radiomics_to_minio #>> clean
#get_input >> get_dicom >> dcmseg2nrrd  >> dcm2nrrd  >> radiomics >> collect_features >> put_radiomics_to_minio #>> clean
