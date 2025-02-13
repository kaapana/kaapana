import glob
import json
import os
from datetime import timedelta
from pathlib import Path

import pydicom
from airflow.exceptions import AirflowSkipException
from airflow.models import DAG
from airflow.utils.dates import days_ago
from airflow.utils.trigger_rule import TriggerRule
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmValidatorOperator import DcmValidatorOperator
from kaapana.operators.GenerateThumbnailOperator import GenerateThumbnailOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalRemoveDicomTagsOperator import (
    LocalRemoveDicomTagsOperator,
from kaapana.operators.LocalAutoTriggerOperator import LocalAutoTriggerOperator
from kaapana.operators.LocalSanitizeProjectAndDatasetOperator import (
    LocalSanitizeProjectAndDatasetOperator,
)
from kaapana.operators.LocalAssignDataToProjectOperator import (
    LocalAssignDataToProjectOperator,
)
from kaapana.operators.LocalClearValidationResultOperator import (
    LocalClearValidationResultOperator,
)
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalDicomSendOperator import LocalDicomSendOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalGetRefSeriesOperator import LocalGetRefSeriesOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalValidationResult2MetaOperator import (
    LocalValidationResult2MetaOperator,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator

args = {
    "ui_visible": False,
    "owner": "system",
    "start_date": days_ago(0),
    "retries": 2,
    "retry_delay": timedelta(seconds=60),
}


dag = DAG(
    dag_id="service-process-incoming-dcm",
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=20,
    tags=["service"],
)


def set_skip_if_dcm_is_no_segmetation(ds, **kwargs):
    """
    Skip the DAG if the incoming DICOM file is not a segmentation.

    Args:
        ds: Unused argument (can be ignored).
        **kwargs: Additional keyword arguments, including the `dag_run` containing the run ID.

    Returns:
        None
    """
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]

    for batch_element_dir in batch_folder:
        input_dir = Path(batch_element_dir) / get_input.operator_out_dir
        dcms = sorted(
            glob.glob(
                os.path.join(input_dir, "*.dcm*"),
                recursive=True,
            )
        )

        if len(dcms) == 0:
            print(
                f"No dicom files found to create metadada {input_dir}. Skipping naive metadata creation."
            )
            raise AirflowSkipException("No DICOM files found")

        ds = pydicom.dcmread(dcms[0])
        if ds.Modality not in ["SEG", "RTSTRUCT"]:
            raise AirflowSkipException("No segmentation found in DICOM file")
    return


get_input = LocalGetInputDataOperator(dag=dag, delete_input_on_success=True)

remove_tags = LocalRemoveDicomTagsOperator(dag=dag, input_operator=get_input)
auto_trigger_operator = LocalAutoTriggerOperator(dag=dag, input_operator=get_input)

sanitize_project_and_dataset = LocalSanitizeProjectAndDatasetOperator(
    dag=dag, input_operator=get_input
)

dcm_send = LocalDicomSendOperator(
    dag=dag,
    input_operator=get_input,
)

extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=get_input)

add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)

assign_to_project = LocalAssignDataToProjectOperator(
    dag=dag, input_operator=extract_metadata
)

push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=get_input, json_operator=extract_metadata
)

validate = DcmValidatorOperator(
    dag=dag,
    input_operator=get_input,
    exit_on_error=False,
)

save_to_meta = LocalValidationResult2MetaOperator(
    dag=dag,
    input_operator=extract_metadata,
    validator_output_dir=validate.operator_out_dir,
    validation_tag="00111001",
    apply_project_context=True,
)

put_html_to_minio = LocalMinioOperator(
    dag=dag,
    action_operator_dirs=[validate.operator_out_dir],
    json_operator=extract_metadata,
    target_dir_prefix="staticwebsiteresults",
    name="put-results-html-to-minio",
    action="put",
    file_white_tuples=(".html"),
)

get_ref_ct_series_from_seg = LocalGetRefSeriesOperator(
    dag=dag,
    input_operator=get_input,
    search_policy="reference_uid",
    parallel_downloads=5,
    parallel_id="ct",
)

generate_segmentation_thumbnail = GenerateThumbnailOperator(
    dag=dag,
    name="generate-segmentation-thumbnail",
    input_operator=get_input,
    orig_image_operator=get_ref_ct_series_from_seg,
)


def upload_thumbnails_into_project_bucket(ds, **kwargs):
    """
    Uploads the generated thumbnails to the project bucket,
    where project is determined from the "00120020 ClinicalTrialProtocolID_keyword" tag of the dicom metadata.
    Additionally uploads the thumbnails to the project bucket of the admin project.
    """
    import json

    import requests
    from kaapanapy.helper import get_minio_client
    from kaapanapy.settings import KaapanaSettings

    kaapana_settings = KaapanaSettings()
    minio = get_minio_client()

    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME
    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]
    for batch_element_dir in batch_folder:
        json_dir = Path(batch_element_dir) / extract_metadata.operator_out_dir
        thumbnail_dir = (
            Path(batch_element_dir) / generate_segmentation_thumbnail.operator_out_dir
        )

        json_files = [f for f in json_dir.glob("*.json")]
        assert len(json_files) == 1
        metadata_file = json_files[0]
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        project_name = metadata.get("00120020 ClinicalTrialProtocolID_keyword")
        response = requests.get(
            f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/{project_name}"
        )
        project = response.json()
        thumbnails = [f for f in thumbnail_dir.glob("*.png")]
        assert len(thumbnails) == 1
        thumbnail_path = thumbnails[0]
        series_uid = metadata.get("0020000E SeriesInstanceUID_keyword")
        minio_object_path = f"thumbnails/{series_uid}.png"
        minio.fput_object(
            bucket_name=project.get("s3_bucket"),
            object_name=minio_object_path,
            file_path=thumbnail_path,
        )

        if project_name != "admin":
            response = requests.get(
                f"http://aii-service.{kaapana_settings.services_namespace}.svc:8080/projects/admin"
            )
            project = response.json()
            minio.fput_object(
                bucket_name=project.get("s3_bucket"),
                object_name=minio_object_path,
                file_path=thumbnail_path,
            )


put_thumbnail_to_project_bucket = KaapanaPythonBaseOperator(
    name="thumbnail_to_project_bucket",
    python_callable=upload_thumbnails_into_project_bucket,
    dag=dag,
)

skip_if_dcm_is_no_segmetation = KaapanaPythonBaseOperator(
    name="skip-if-dcm-is-no-segmentation",
    pool="default_pool",
    pool_slots=1,
    python_callable=set_skip_if_dcm_is_no_segmetation,
    dag=dag,
)

clean = LocalWorkflowCleanerOperator(
    dag=dag,
    clean_workflow_dir=True,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
)

get_input >> auto_trigger_operator
get_input >> [extract_metadata, skip_if_dcm_is_no_segmetation]
extract_metadata >> [
    push_json,
    add_to_dataset,
    assign_to_project,
    validate,
    remove_tags,
]

(remove_tags >> dcm_send)

(validate >> save_to_meta >> put_html_to_minio)

(
    skip_if_dcm_is_no_segmetation
    >> get_ref_ct_series_from_seg
    >> generate_segmentation_thumbnail
    >> put_thumbnail_to_project_bucket
)

[
    push_json,
    add_to_dataset,
    assign_to_project,
    dcm_send,
    put_html_to_minio,
    put_thumbnail_to_project_bucket,
] >> clean
