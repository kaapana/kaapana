from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from nnunet.LocalSegCheckOperator import LocalSegCheckOperator

from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.LocalNnUnetDatasetOperator import LocalNnUnetDatasetOperator
from nnunet.LocalDagTriggerOperator import LocalDagTriggerOperator

TASK_NAME = "Task042_Training"

ui_forms = {
    "publication_form": {
        "type": "object",
        "properties": {
            "title": {
                "title": "Title",
                "default": "Automated Design of Deep Learning Methods\n for Biomedical Image Segmentation",
                "type": "string",
                "readOnly": True,
            },
            "authors": {
                "title": "Authors",
                "default": "Fabian Isensee, Paul F. Jäger, Simon A. A. Kohl, Jens Petersen, Klaus H. Maier-Hein",
                "type": "string",
                "readOnly": True,
            },
            "link": {
                "title": "DOI",
                "default": "https://arxiv.org/abs/1904.08128",
                "description": "DOI",
                "type": "string",
                "readOnly": True,
            },
            "confirmation": {
                "title": "Accept",
                "default": False,
                "type": "boolean",
                "readOnly": True,
                "required": True,
            }
        }
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "TASK_NAME",
                "description": "Specify a name for the training task",
                "type": "string",
                "default": TASK_NAME,
                "required": True
            },
            "training_description": {
                "title": "Training description",
                "default": "nnUnet Segmentation",
                "description": "Specify a version.",
                "type": "string",
                "readOnly": False,
            },
            "licence": {
                "title": "Licence",
                "default": "None",
                "description": "Specify a licence.",
                "type": "string",
                "readOnly": False,
            },
            "version": {
                "title": "Version",
                "default": "None",
                "description": "Specify a version.",
                "type": "string",
                "readOnly": False,
            },
            "training_reference": {
                "title": "Training reference",
                "default": "nnUNet",
                "description": "Set a reference.",
                "type": "string",
                "readOnly": False,
            },
            "shuffle_seed": {
                "title": "Shuffle seed",
                "default": 0,
                "description": "Set a seed.",
                "type": "integer",
                "readOnly": False,
            },
            "test_percentage": {
                "title": "Test percentage",
                "default": 0,
                "description": "Set % of data for the test-set.",
                "type": "integer",
                "readOnly": False,
            },
            "copy_data": {
                "title": "Copy_data",
                "description": "Copy data?",
                "default": True,
                "type": "boolean",
                "readOnly": False,
            },
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
            },
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
    dag_id='nnunet-train',
    default_args=args,
    concurrency=5,
    max_active_runs=2,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(dag=dag, check_modality=True)
dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=get_input,
    output_type="nii.gz",
    seg_filter="liver",
    parallel_id='seg',
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(dag=dag, input_operator=get_input, search_policy="reference_uid", modality=None)
dcm2nifti_ct = DcmConverterOperator(dag=dag, input_operator=get_ref_ct_series_from_seg, parallel_id='ct', output_format='nii.gz')

check_seg = LocalSegCheckOperator(
    dag=dag,
    input_operator=dcm2nifti_seg,
    dicom_input_operator=get_ref_ct_series_from_seg
)
# trigger_preprocessing = LocalDagTriggerOperator(dag=dag,
#                                                 trigger_dag_id='ct-pet-prep',
#                                                 cache_operators=["modality-nifti","seg-nifti"],
#                                                 target_bucket="nnunet-prep",
#                                                 trigger_mode="single",
#                                                 wait_till_done=True,
#                                                 use_dcm_files=False
#                                                 )

# training_data_preparation = LocalNnUnetDatasetOperator(
#     dag=dag,
#     task_name=TASK_NAME,
#     modality={
#         "0": "CT"
#     },
#     labels={
#         "0": "background",
#         "1": "Liver",
#         # "2": "Tumor"
#     },
#     input_operators=dcm2nifti_ct,
#     seg_input_operator=dcm2nifti_seg,
#     licence="NA",
#     version="NA",
#     tensor_size="3D",
#     test_percentage=0,
#     copy_target_data=True,
#     shuffle_seed=None,
# )

nnunet_preprocess = NnUnetOperator(
    dag=dag,
    mode="preprocess",
    label_operator=dcm2nifti_seg,
    nifti_input_operators=[dcm2nifti_ct],
    dicom_input_operators=[get_ref_ct_series_from_seg],
    processes_low=1,
    processes_full=1,
    parallel_id="dataset",
)

nnunet_train = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="training",
    task_name=TASK_NAME,
    input_operator=nnunet_preprocess
)

#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> check_seg >> nnunet_preprocess
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> check_seg >> nnunet_preprocess >> nnunet_train
# >> clean
