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
from nnunet_training.NnUnetOperator import NnUnetOperator
from nnunet_training.LocalNnUnetDatasetOperator import LocalNnUnetDatasetOperator
from nnunet_training.LocalDagTriggerOperator import LocalDagTriggerOperator

TASK_NAME = "Task042_LiverTest"

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
            "input": {
                "title": "Input Modality",
                "default": "SEG",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": True,
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

# trigger_preprocessing = LocalDagTriggerOperator(dag=dag,
#                                                 trigger_dag_id='ct-pet-prep',
#                                                 cache_operators=["modality-nifti","seg-nifti"],
#                                                 target_bucket="nnunet-prep",
#                                                 trigger_mode="single",
#                                                 wait_till_done=True,
#                                                 use_dcm_files=False
#                                                 )

training_data_preparation = LocalNnUnetDatasetOperator(
    dag=dag,
    task_name=TASK_NAME,
    modality={
        "0": "CT"
    },
    labels={
        "0": "background",
        "1": "Liver",
        # "2": "Tumor"
    },
    input_operators=dcm2nifti_ct,
    seg_input_operator=dcm2nifti_seg,
    licence="NA",
    version="NA",
    tensor_size="3D",
    test_percentage=0,
    copy_target_data=True,
    shuffle_seed=None,
)

nnunet_check_dataset = NnUnetOperator(
    dag=dag,
    mode="preprocess",
    processes_low=8,
    processes_full=6,
    parallel_id="prep",
    task_name=TASK_NAME,
    input_operator=training_data_preparation
)

nnunet_train = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="training",
    task_name=TASK_NAME,
    input_operator=training_data_preparation
)
#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> training_data_preparation
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> training_data_preparation >> nnunet_check_dataset >> nnunet_train
# >> clean
