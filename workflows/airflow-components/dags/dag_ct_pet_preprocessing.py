from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.models import DAG
from airflow.utils.dates import days_ago
from datetime import timedelta

from ct_pet_prediction.LocalGetInputDataOperator import LocalGetInputDataOperator
from ct_pet_prediction.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from ct_pet_prediction.LocalDatasetSplitOperator import LocalDatasetSplitOperator
from ct_pet_prediction.CtPetPredictionTrainingOperator import CtPetPredictionTrainingOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from ct_pet_prediction.MaskCtOperator import MaskCtOperator
from ct_pet_prediction.NormalizationOperator import NormalizationOperator
from ct_pet_prediction.ResampleCtPetOperator import ResampleCtPetOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator 

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "input": {
                "title": "Input",
                "default": "PT",
                "description": "Input-data modality",
                "type": "string",
                "readOnly": True,
            },
        }
    }
}

args = {
    'ui_visible': False,
    'ui_forms': ui_forms,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='ct-pet-prep',
    default_args=args,
    max_active_runs=6,
    # concurrency=15,
    schedule_interval=None)

get_input = LocalGetInputDataOperator(dag=dag)
get_ref_ct_series_from_pet = LocalGetRefSeriesOperator(dag=dag,input_operator=get_input, search_policy="study_uid",modality="CT")
dcm2niftiPet = DcmConverterOperator(dag=dag,input_operator=get_input, parallel_id='pet', output_format='nii.gz')
dcm2niftiCt = DcmConverterOperator(dag=dag, input_operator=get_ref_ct_series_from_pet, parallel_id='ct', output_format='nii.gz')
resample = ResampleCtPetOperator(dag=dag, ct_nifti_operator=dcm2niftiCt, pet_nifti_operator=dcm2niftiPet)
create_mask = MaskCtOperator(dag=dag,input_operator=resample)
normalization = NormalizationOperator(dag=dag, resampling_operator=resample, mask_operator=create_mask)
put_to_minio = LocalMinioOperator(dag=dag, action='put', action_operators=[normalization], bucket_name="ctpet-prep", file_white_tuples=('.npy'),zip_files=False)
clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> get_ref_ct_series_from_pet >> dcm2niftiCt >> resample >> create_mask >> normalization >> put_to_minio >> clean
get_input >> dcm2niftiPet >> resample
