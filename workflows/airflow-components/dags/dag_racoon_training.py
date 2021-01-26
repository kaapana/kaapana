from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from datetime import datetime
from airflow.api.common.experimental import pool as pool_api
import pydicom

from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.DcmSeg2ItkOperator import DcmSeg2ItkOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator

from racoon_training.NnUnetOperator import NnUnetOperator
from racoon_training.LocalNnUnetDatasetOperator import LocalNnUnetDatasetOperator
from racoon_training.LocalDagTriggerOperator import LocalDagTriggerOperator
from racoon_training.LocalSegCheckOperator import LocalSegCheckOperator
from racoon_training.Bin2DcmOperator import Bin2DcmOperator
from racoon_training.ZipUnzipOperator import ZipUnzipOperator

from kaapana.operators.Pdf2DcmOperator import Pdf2DcmOperator

TASK_NAME = "Task100_RACOON"
seg_filter = ""
prep_modalities = "CT"
train_network = "3d_lowres"
train_network_trainer = "nnUNetTrainerV2"

study_uid = pydicom.uid.generate_uid()

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
                "enum": ["2d", "3d_lowres", "3d_fullres", "3d_cascade_fullres"],
                "type": "string",
                "readOnly": False,
                "required": True
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
                "description": "Select organ for multi-label DICOM SEGs: eg 'liver' or 'spleen,liver'",
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
    'retries': 1,
    'retry_delay': timedelta(seconds=30)
}

dag = DAG(
    dag_id='racoon-train',
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
    retries=0
)

nnunet_train = NnUnetOperator(
    dag=dag,
    mode="training",
    input_operator=nnunet_preprocess,
    train_network=train_network,
    train_network_trainer=train_network_trainer,
    train_fold='all',
    retries=0
)

# pdf2dcm = Pdf2DcmOperator(
#     dag=dag,
#     dicom_operator=get_input,
#     input_operator=identify_best,
#     pdf_title=f"Training Report {study_uid}"
#     )

zip_model = ZipUnzipOperator(
    dag=dag,
    target_filename = f"racoon_nnunet_{train_network}.zip",
    subdir="results/nnUNet",
    mode="zip",
    batch_level=True,
    input_operator=nnunet_train
)

bin2dcm = Bin2DcmOperator(
    dag=dag,
    name="model2dicom",
    patient_id="",
    study_uid=study_uid,
    study_description="nnUNet model trained for RACOON",
    study_id="RACOON",
    size_limit=100,
    input_operator=zip_model,
    file_extensions="*.zip"
)

dcmseg_send = DcmSendOperator(
    dag=dag,
    level="batch",
    ae_title="racoon-models",
    input_operator=bin2dcm
)


#clean = LocalWorkflowCleanerOperator(dag=dag,clean_workflow_dir=True)

get_input >> dcm2nifti_seg >> check_seg >> nnunet_preprocess
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_ct >> check_seg >> nnunet_preprocess

nnunet_preprocess >> nnunet_train >> zip_model >> bin2dcm >> dcmseg_send  # >> clean
