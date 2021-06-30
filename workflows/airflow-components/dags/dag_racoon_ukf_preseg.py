from airflow.utils.dates import days_ago
from airflow.models import DAG
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.Json2DcmSROperator import Json2DcmSROperator
from kaapana.operators.DcmModifyOperator import DcmModifyOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from racoon_ukf_preseg.PresegmentationOperator import PresegmentationOperator
from datetime import timedelta

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
    'owner': 'UKF',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='racoon-ukf-presegmentation',
    default_args=args,
    concurrency=50,
    max_active_runs=5,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    operator_out_dir="initial-input"
)

nnunet_predict = PresegmentationOperator(
    dag=dag,
    input_operator=get_input
)

nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=dag.dag_id,
    skip_empty_slices=True,
    alg_name=dag.dag_id
)

json2dicomSR = Json2DcmSROperator(
    dag=dag,
    input_operator=nnunet_predict,
    src_dicom_operator=get_input,
    seg_dicom_operator=nrrd2dcmSeg_multi,
    input_file_extension="volumes.json",
)

dcmModify = DcmModifyOperator(
    dag=dag,
    input_operator=json2dicomSR,
    dicom_tags_to_modify="(0008,0016)=1.2.840.10008.5.1.4.1.1.88.11"
)
dcmseg_send_seg = DcmSendOperator(dag=dag, input_operator=nrrd2dcmSeg_multi, parallel_id="seg")
dcmseg_send_sr = DcmSendOperator(dag=dag, input_operator=json2dicomSR, parallel_id="sr")
clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

get_input >> nnunet_predict >> nrrd2dcmSeg_multi >> dcmseg_send_seg >> clean
nrrd2dcmSeg_multi >> json2dicomSR >> dcmModify >> dcmseg_send_sr >> clean
