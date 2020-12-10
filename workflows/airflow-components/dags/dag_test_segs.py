from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.GetTaskModelOperator import GetTaskModelOperator
from nnunet_training.LocalSegCheckOperator import LocalSegCheckOperator
# from nnunet.GetContainerModelOperator import GetContainerModelOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator

import pathlib
import json
import os


args = {
    'ui_visible': True,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 0,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='seg_test',
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
get_task_model = GetTaskModelOperator(dag=dag)
# get_task_model = GetContainerModelOperator(dag=dag)
dcm2nifti = DcmConverterOperator(dag=dag, input_operator=get_input, output_format='nii.gz')
nnunet_predict = NnUnetOperator(dag=dag, input_dirs=[dcm2nifti.operator_out_dir], input_operator=dcm2nifti)

alg_name = nnunet_predict.image.split("/")[-1].split(":")[0]
nrrd2dcmSeg_multi = Itk2DcmSegOperator(
    dag=dag,
    input_operator=get_input,
    segmentation_operator=nnunet_predict,
    input_type="multi_label_seg",
    multi_label_seg_name=alg_name,
    alg_name=alg_name
)

dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=nrrd2dcmSeg_multi,
    output_type="nii.gz",
    seg_filter="liver",
    parallel_id='seg',
)

check_seg = LocalSegCheckOperator(
    dag=dag,
    input_operator=dcm2nifti_seg,
    dicom_input_operator=get_input
)

clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> get_task_model >> dcm2nifti >> nnunet_predict >> nrrd2dcmSeg_multi >> dcm2nifti_seg >> check_seg >> clean
