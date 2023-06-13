from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalDcmAnonymizerOperator import LocalDcmAnonymizerOperator
from kaapana.operators.LocalConcatJsonOperator import LocalConcatJsonOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalExtractImgIntensitiesOperator import (
    LocalExtractImgIntensitiesOperator,
)
from kaapana.operators.LocalExtractSegMetadataOperator import (
    LocalExtractSegMetadataOperator,
)
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.Mask2nifitiOperator import Mask2nifitiOperator
from kaapana.operators.LocalMergeBranchesOperator import LocalMergeBranchesOperator

from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from airflow.utils.trigger_rule import TriggerRule

log = LoggingMixin().log

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
        },
    }
}

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="advanced-collect-metadata",
    default_args=args,
    concurrency=50,
    max_active_runs=50,
    schedule_interval=None,
)

### COMMON ###
get_input = LocalGetInputDataOperator(dag=dag)

anonymizer = LocalDcmAnonymizerOperator(
    dag=dag, input_operator=get_input, single_slice=True
)

extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=anonymizer)

### SPLITTED: BRANCH CT, MR IMAGE ###
dcm2nifti_ct = DcmConverterOperator(
    dag=dag,
    input_operator=get_input,
    output_format="nii.gz",
)

extract_img_intensities = LocalExtractImgIntensitiesOperator(
    dag=dag,
    input_operator=dcm2nifti_ct,
    json_operator=extract_metadata,
)

### SPLITTED: BRANCH SEG ###
dcm2nifti_seg = Mask2nifitiOperator(
    dag=dag,
    input_operator=get_input,
    dicom_operator=get_input,
    exit_on_error=False,
    retries=0,
    image_pull_policy="Always",
)

extract_seg_metadata = LocalExtractSegMetadataOperator(
    dag=dag,
    input_operator=dcm2nifti_seg,
    json_operator=extract_metadata,
)

### COMMON ###
merge_branches = LocalMergeBranchesOperator(
    dag=dag,
    first_input_operator=extract_img_intensities,
    second_input_operator=extract_seg_metadata,
    trigger_rule=TriggerRule.ALL_DONE,
)

concat_metadata = LocalConcatJsonOperator(
    dag=dag,
    name="concatenated-metadata",
    input_operator=merge_branches,
    # trigger_rule=TriggerRule.ALL_DONE,
)

put_to_minio = LocalMinioOperator(
    dag=dag,
    action="put",
    action_operators=[concat_metadata],
    bucket_name="downloads",
    zip_files=True,
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=False)

(
    get_input
    >> anonymizer
    >> extract_metadata
    >> dcm2nifti_ct
    >> extract_img_intensities
    >> merge_branches
    >> concat_metadata
    >> put_to_minio
    >> clean
)
extract_metadata >> dcm2nifti_seg >> extract_seg_metadata >> merge_branches
