import random
from datetime import datetime, timedelta

from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.Bin2DcmOperator import Bin2DcmOperator
from kaapana.operators.Pdf2DcmOperator import Pdf2DcmOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from airflow.api.common.experimental import pool as pool_api
from nnunet.NnUnetOperator import NnUnetOperator
from nnunet.SegCheckOperator import SegCheckOperator
from nnunet.NnUnetNotebookOperator import NnUnetNotebookOperator
from airflow.utils.dates import days_ago
from airflow.models import DAG
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import (
    INSTANCE_NAME,
    SERVICES_NAMESPACE,
    GPU_COUNT,
    CPU_CORE_COUNT,
)

study_id = "Kaapana"
TASK_NAME = f"Task{random.randint(100,999):03}_{INSTANCE_NAME}_{datetime.now().strftime('%d%m%y-%H%M')}"
seg_filter = ""
prep_modalities = "CT"
default_model = "3d_lowres"
train_network_trainer = "nnUNetTrainerV2"
ae_title = "nnUnet-results"
max_epochs = 1000
num_batches_per_epoch = 250
num_val_batches_per_epoch = 50
dicom_model_slice_size_limit = 70
training_results_study_uid = None
prep_threads = 2

print(f"### nnunet-training GPU_COUNT {GPU_COUNT}")
max_active_runs = GPU_COUNT if GPU_COUNT != 0 else 1
print(f"### nnunet-training max_active_runs {max_active_runs}")

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
                "readOnly": False,
                "required": True,
            },
        },
    },
    "workflow_form": {
        "type": "object",
        "properties": {
            "task": {
                "title": "TASK_NAME",
                "description": "Specify a name for the training task",
                "type": "string",
                "default": TASK_NAME,
                "required": True,
            },
            "model": {
                "title": "Network",
                "default": default_model,
                "description": "2d, 3d_lowres, 3d_fullres or 3d_cascade_fullres",
                "enum": ["2d", "3d_lowres", "3d_fullres", "3d_cascade_fullres"],
                "type": "string",
                "readOnly": False,
                "required": True,
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
            "instance_name": {
                "title": "Instance name",
                "description": "Specify an ID for the node / site",
                "type": "string",
                "default": INSTANCE_NAME,
                "required": True,
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
            "body_part": {
                "title": "Body Part",
                "description": "Body part, which needs to be present in the image.",
                "default": "N/A",
                "type": "string",
                "readOnly": False,
            },
            "train_max_epochs": {
                "title": "Epochs",
                "default": max_epochs,
                "description": "Specify max epochs.",
                "type": "integer",
                "required": True,
                "readOnly": False,
            },
            "num_batches_per_epoch": {
                "title": "Batches per epoch",
                "default": num_batches_per_epoch,
                "description": "Do only change if you know what you are doing!.",
                "type": "integer",
                "required": True,
                "readOnly": False,
            },
            "num_val_batches_per_epoch": {
                "title": "Validation batches per epoch",
                "default": num_val_batches_per_epoch,
                "description": "Do only change if you know what you are doing!.",
                "type": "integer",
                "required": True,
                "readOnly": False,
            },
            "fp32": {
                "type": "boolean",
                "title": "FP32",
                "default": False,
                "description": "Disable mixed precision training and run old school fp32",
            },
            "prep_preprocess": {
                "type": "boolean",
                "title": "Execute preprocessing",
                "default": True,
                "description": "Set this flag if you dont want to run the preprocessing. If this is set then this script will only run the experiment planning and create the plans file",
            },
            "prep_check_integrity": {
                "type": "boolean",
                "title": "Check integrity",
                "default": True,
                "description": "Whether to check integrity of data",
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
                "default": "SEG,RTSTRUCT",
                "description": "Expected input modality.",
                "type": "string",
                "readOnly": False,
                "required": True,
            },
            "single_execution": {
                "type": "boolean",
                "title": "Single execution",
                "description": "Whether your report is execute in single mode or not",
                "default": False,
                "readOnly": True,
                # "required": True
            },
        },
    },
}
args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="nnunet-training",
    default_args=args,
    concurrency=2 * max_active_runs,
    max_active_runs=max_active_runs,
    schedule_interval=None,
)

get_input = LocalGetInputDataOperator(
    dag=dag, check_modality=True, parallel_downloads=5
)


get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
    modality=None,
)

dcm2nifti_seg = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_input,
    dicom_operator=get_ref_ct_series_from_seg,
    seg_filter=seg_filter,
)

dcm2nifti_ct = DcmConverterOperator(
    dag=dag, input_operator=get_ref_ct_series_from_seg, output_format="nii.gz"
)

check_seg = SegCheckOperator(
    dag=dag,
    input_operator=dcm2nifti_seg,
    original_img_operator=dcm2nifti_ct,
    parallel_processes=3,
    delete_merged_data=True,
    fail_if_overlap=False,
    fail_if_label_already_present=False,
    fail_if_label_id_not_extractable=False,
    force_same_labels=False,
)

nnunet_preprocess = NnUnetOperator(
    dag=dag,
    mode="preprocess",
    input_modality_operators=[dcm2nifti_ct],
    prep_label_operators=[check_seg],
    prep_use_nifti_labels=False,
    prep_modalities=prep_modalities.split(","),
    prep_processes_low=prep_threads + 1,
    prep_processes_full=prep_threads,
    prep_preprocess=True,
    prep_check_integrity=True,
    prep_copy_data=True,
    prep_exit_on_issue=True,
    retries=0,
    instance_name=INSTANCE_NAME,
    allow_federated_learning=True,
    whitelist_federated_learning=["dataset_properties.pkl", "intensityproperties.pkl"],
    trigger_rule=TriggerRule.NONE_FAILED,
    dev_server=None,  #'code-server'
)

nnunet_train = NnUnetOperator(
    dag=dag,
    mode="training",
    train_max_epochs=max_epochs,
    input_operator=nnunet_preprocess,
    model=default_model,
    allow_federated_learning=True,
    train_network_trainer=train_network_trainer,
    train_fold="all",
    dev_server=None,
    retries=0,
)

generate_nnunet_report = NnUnetNotebookOperator(
    dag=dag,
    name="generate-nnunet-report",
    input_operator=nnunet_train,
    arguments=["/kaapana/app/notebooks/nnunet_training/run_generate_nnunet_report.sh"],
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-nnunet-data",
    zip_files=True,
    action="put",
    action_operators=[nnunet_train, generate_nnunet_report],
    file_white_tuples=(".zip"),
)

put_report_to_minio = LocalMinioOperator(
    dag=dag,
    name="upload-staticwebsiteresults",
    bucket_name="staticwebsiteresults",
    action="put",
    action_operators=[generate_nnunet_report],
    file_white_tuples=(".html", ".pdf"),
)

pdf2dcm = Pdf2DcmOperator(
    dag=dag,
    input_operator=generate_nnunet_report,
    study_uid=training_results_study_uid,
    aetitle=ae_title,
    pdf_title=f"Training Report nnUNet {TASK_NAME} {datetime.now().strftime('%d.%m.%Y %H:%M')}",
)

dcmseg_send_pdf = DcmSendOperator(
    dag=dag,
    parallel_id="pdf",
    level="batch",
    pacs_host=f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc",
    pacs_port="11112",
    ae_title=ae_title,
    input_operator=pdf2dcm,
)

zip_model = ZipUnzipOperator(
    dag=dag,
    target_filename=f"nnunet_model.zip",
    whitelist_files="model_latest.model.pkl,model_latest.model,model_final_checkpoint.model,model_final_checkpoint.model.pkl,plans.pkl,*.json,*.png,*.pdf",
    subdir="results/nnUNet",
    mode="zip",
    batch_level=True,
    input_operator=nnunet_train,
)

bin2dcm = Bin2DcmOperator(
    dag=dag,
    dataset_info_operator=nnunet_preprocess,
    name="model2dicom",
    patient_name="nnUNet-model",
    patient_id=INSTANCE_NAME,
    instance_name=INSTANCE_NAME,
    manufacturer="Kaapana",
    manufacturer_model="nnUNet",
    version=nnunet_train.image.split(":")[-1],
    study_id=study_id,
    study_uid=training_results_study_uid,
    protocol_name=None,
    study_description=None,
    series_description=f"nnUNet model {datetime.now().strftime('%d.%m.%Y %H:%M')}",
    size_limit=dicom_model_slice_size_limit,
    input_operator=zip_model,
    file_extensions="*.zip",
)

dcm_send_int = DcmSendOperator(
    dag=dag,
    level="batch",
    pacs_host=f"ctp-dicom-service.{SERVICES_NAMESPACE}.svc",
    pacs_port="11112",
    ae_title=ae_title,
    input_operator=bin2dcm,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)
get_input >> get_ref_ct_series_from_seg >> dcm2nifti_seg >> check_seg
(
    get_input
    >> get_ref_ct_series_from_seg
    >> dcm2nifti_ct
    >> check_seg
    >> nnunet_preprocess
    >> nnunet_train
)

(
    nnunet_train
    >> generate_nnunet_report
    >> put_to_minio
    >> put_report_to_minio
    >> pdf2dcm
    >> dcmseg_send_pdf
    >> clean
)
nnunet_train >> zip_model >> bin2dcm >> dcm_send_int >> clean
