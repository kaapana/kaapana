from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

from kaapana.blueprints.json_schema_templates import schema_upload_form
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.Itk2DcmSegOperator import Itk2DcmSegOperator
from kaapana.operators.Itk2DcmOperator import Itk2DcmOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from kaapana.operators.DcmSendOperator import DcmSendOperator
from kaapana.operators.ZipUnzipOperator import ZipUnzipOperator
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR
from kaapana.operators.LocalVolumeMountOperator import LocalVolumeMountOperator

from pathlib import Path

ui_forms = {
    **schema_upload_form(
        whitelisted_file_formats=(".zip"),
    ),
    "workflow_form": {
        "type": "object",
        "properties": {
            "modality": {
                "title": "Modality",
                "description": "Modality of the input images. Usually CT or MR.",
                "type": "string",
                "default": "",
                "required": False,
            },
            "aetitle": {
                "title": "Tag",
                "description": "Specify a tag for your dataset.",
                "type": "string",
                "default": "itk2dcm",
                "required": True,
            },
            "delete_original_file": {
                "title": "Delete file from file system after successful import?",
                "type": "boolean",
                "default": True,
            },
        },
    },
}

log = LoggingMixin().log

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="convert-nifitis-to-dicoms-and-import-to-pacs",
    default_args=args,
    schedule_interval=None,
    tags= ["import"]
)

get_object_from_uploads = LocalVolumeMountOperator(
    dag=dag,
    mount_path="/kaapana/app/uploads",
    action="get",
    keep_directory_structure=False,
    name="get-uploads",
    whitelisted_file_endings=(".zip",),
    trigger_rule="none_failed",
    operator_out_dir="itk",
)

unzip_files = ZipUnzipOperator(
    dag=dag,
    input_operator=get_object_from_uploads,
    batch_level=True,
    mode="unzip",
)

convert = Itk2DcmOperator(
    dag=dag,
    name="convert-itk2dcm",
    trigger_rule="none_failed_min_one_success",
    input_operator=unzip_files,
)

convert_seg = Itk2DcmSegOperator(
    dag=dag,
    name="convert-segmentation",
    input_operator=convert,
    segmentation_in_dir="segmentations",
    input_type="multi_label_seg",
    skip_empty_slices=True,
    fail_on_no_segmentation_found=False
)

dcm_send_seg = DcmSendOperator(name="dcm-send-seg", dag=dag, input_operator=convert_seg)

dcm_send_img = DcmSendOperator(
    name="dcm-send-img",
    dag=dag,
    input_operator=convert,
)

remove_object_from_uploads = LocalVolumeMountOperator(
    dag=dag, name="removing-object-from-uploads", mount_path="/kaapana/app/uploads", action="remove", whitelisted_file_endings=(".zip",)
)

clean = LocalWorkflowCleanerOperator(
    dag=dag, trigger_rule="none_failed_min_one_success", clean_workflow_dir=True
)


def branching_zipping_callable(**kwargs):
    download_dir = (
        Path(AIRFLOW_WORKFLOW_DIR)
        / kwargs["dag_run"].run_id
        / get_object_from_uploads.operator_out_dir
    )
    conf = kwargs["dag_run"].conf
    if "action_files" in conf["data_form"]:
        return [unzip_files.name]
    else:
        unzip_dir = download_dir.parents[0] / unzip_files.operator_out_dir
        unzip_dir.mkdir(parents=True, exist_ok=True)
        download_dir.rename(unzip_dir)
        return [convert.name]


branching_zipping = BranchPythonOperator(
    task_id="branching-unzipping",
    provide_context=True,
    python_callable=branching_zipping_callable,
    dag=dag,
)


def branching_sending_callable(**kwargs):
    run_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id
    if [p for p in run_dir.rglob("seg_info.json")]:
        return [convert_seg.name, dcm_send_img.name]
    else:
        return [dcm_send_img.name]


branching_sending = BranchPythonOperator(
    task_id="branching-sending",
    provide_context=True,
    python_callable=branching_sending_callable,
    dag=dag,
)


def branching_cleaning_uploads_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    delete_original_file = conf["workflow_form"]["delete_original_file"]
    if delete_original_file:
        return [remove_object_from_uploads.name]
    else:
        return [clean.name]


branching_cleaning_uploads = BranchPythonOperator(
    task_id="branching-cleaning-uploads",
    provide_context=True,
    trigger_rule="none_failed_min_one_success",
    python_callable=branching_cleaning_uploads_callable,
    dag=dag,
)


get_object_from_uploads >> branching_zipping
branching_zipping >> unzip_files >> convert
branching_zipping >> convert
convert >> branching_sending
branching_sending >> convert_seg >> dcm_send_seg >> branching_cleaning_uploads
branching_sending >> dcm_send_img >> branching_cleaning_uploads
branching_cleaning_uploads >> remove_object_from_uploads >> clean
branching_cleaning_uploads >> clean
