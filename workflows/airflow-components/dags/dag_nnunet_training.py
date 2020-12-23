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
from kaapana.operators.LocalMinioOperator import LocalMinioOperator 

from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.LocalNnUnetDatasetOperator import LocalNnUnetDatasetOperator
from nnunet.LocalDagTriggerOperator import LocalDagTriggerOperator
from nnunet.LocalSegCheckOperator import LocalSegCheckOperator
from airflow.api.common.experimental import pool as pool_api

TASK_NAME = "Task042_Training"
seg_filter = ""
prep_modalities = "CT"
train_network = "2d"
train_network_trainer = "nnUNetTrainerV2"

cpu_count_pool = pool_api.get_pool(name="CPU")
prep_threads = int(cpu_count_pool.slots//8) if cpu_count_pool is not None else 4
prep_threads = 2 if prep_threads < 2 else prep_threads
prep_threads = 9 if prep_threads > 9 else prep_threads

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
            "train_network": {
                "title": "Network",
                "default": train_network,
                "description": "2d, 3d_lowres, 3d_fullres or 3d_cascade_fullres",
                "type": "string",
                "readOnly": False,
            },
            "train_network_trainer": {
                "title": "Network-trainer",
                "default": train_network_trainer,
                "description": "nnUNetTrainerV2 or nnUNetTrainerV2CascadeFullRes",
                "type": "string",
                "readOnly": False,
            },
            "prep_modalities": {
                "title": "Modalities",
                "default": prep_modalities,
                "description": "eg 'CT' or 'CT,PET' etc.",
                "type": "string",
                "readOnly": False,
            },
            "seg_filter": {
                "title": "Seg",
                "default": seg_filter,
                "description": "Select organ for multi-label DICOM SEGs: eg 'liver' or 'spleen;liver'",
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
            "training_description": {
                "title": "Training description",
                "default": "nnUnet Segmentation",
                "description": "Specify a version.",
                "type": "string",
                "readOnly": False,
            },
            # "version": {
            #     "title": "Version",
            #     "default": "0.0.1-alpha",
            #     "description": "Specify a version.",
            #     "type": "string",
            #     "readOnly": False,
            # },
            # "training_reference": {
            #     "title": "Training reference",
            #     "default": "nnUNet",
            #     "description": "Set a reference.",
            #     "type": "string",
            #     "readOnly": False,
            # },
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
    concurrency=1,
    max_active_runs=1,
    schedule_interval=None
)

get_input = LocalGetInputDataOperator(
    dag=dag,
    check_modality=True,
    parallel_downloads=5
)
dcm2nifti_seg = DcmSeg2ItkOperator(
    dag=dag,
    input_operator=get_input,
    output_type="nii.gz",
    seg_filter=seg_filter,
    parallel_id='seg',
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    modality=None
)
dcm2nifti_ct = DcmConverterOperator(dag=dag, input_operator=get_ref_ct_series_from_seg, parallel_id='ct', output_format='nii.gz')

check_seg = LocalSegCheckOperator(
    dag=dag,
    move_data=True,
    input_operators=[get_input, dcm2nifti_seg, get_ref_ct_series_from_seg, dcm2nifti_ct]
)

nnunet_preprocess = NnUnetOperator(
    dag=dag,
    mode="preprocess",
    input_nifti_operators=[dcm2nifti_ct],
    prep_label_operator=dcm2nifti_seg,
    prep_modalities=prep_modalities.split(","),
    prep_processes_low=prep_threads+1,
    prep_processes_full=prep_threads,
    prep_preprocess=True,
    prep_check_integrity=True,
)

nnunet_train_fold0 = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="fold-0",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold=0
)

nnunet_train_fold1 = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="fold-1",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold=1
)

nnunet_train_fold2 = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="fold-2",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold=2
)

nnunet_train_fold3 = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="fold-3",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold=3
)

nnunet_train_fold4 = NnUnetOperator(
    dag=dag,
    mode="training",
    parallel_id="fold-4",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold=4
)

identify_best = NnUnetOperator(
    dag=dag,
    mode="identify-best",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
)

nnunet_export = NnUnetOperator(
    dag=dag,
    mode="export-model",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    action='put',
    action_operators=[nnunet_export],
    bucket_name="nnunet-models",
    file_white_tuples=('.zip'),
    zip_files=False
)

#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> check_seg >> nnunet_preprocess
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> check_seg >> nnunet_preprocess

nnunet_preprocess >> nnunet_train_fold0 >> identify_best
nnunet_preprocess >> nnunet_train_fold1 >> identify_best
nnunet_preprocess >> nnunet_train_fold2 >> identify_best
nnunet_preprocess >> nnunet_train_fold3 >> identify_best
nnunet_preprocess >> nnunet_train_fold4 >> identify_best

identify_best >> nnunet_export >> put_to_minio #>> clean

