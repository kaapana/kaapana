from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.DcmConverterOperator import DcmConverterOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.MinioOperator import MinioOperator
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.KaapanaBranchPythonBaseOperator import (
    KaapanaBranchPythonBaseOperator,
)

log = LoggingMixin().log

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "convert_to_nifti": {
                "title": "Convert to nifti format",
                "type": "boolean",
                "description": "Supported for DCM Image, DCM RT Dose and DCM Seg",
                "default": False,
            },
            "zip_files": {
                "title": "Compress files",
                "type": "boolean",
                "description": "Should the files be compressed into a zip file?",
                "default": True,
            },
            "single_execution": {
                "title": "single execution",
                "description": "Should each series be processed separately?",
                "type": "boolean",
                "default": False,
                "readOnly": False,
            },
        },
    }
}

args = {
    "ui_visible": True,
    "ui_forms": ui_forms,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 1,
    "retry_delay": timedelta(seconds=30),
}

dag = DAG(
    dag_id="download-selected-files",
    default_args=args,
    concurrency=10,
    max_active_runs=10,
    schedule_interval=None,
)


class BranchIfNiftiOperator(KaapanaBranchPythonBaseOperator):
    def branch_if_nifti(self, ds, **kwargs):
        conf = kwargs["dag_run"].conf
        print("conf", conf)

        convert_to_nifti = bool(conf["form_data"]["convert_to_nifti"])

        if convert_to_nifti:
            return "dcm-converter"
        else:
            return "minio-actions-put-dicom"

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag,
            name="branch-nifti-conversion",
            python_callable=self.branch_if_nifti,
            **kwargs
        )


get_input = GetInputOperator(dag=dag)
branch_if_nifti = BranchIfNiftiOperator(dag=dag)
dcm2nifti = DcmConverterOperator(
    dag=dag, input_operator=get_input, output_format="nii.gz"
)

put_to_minio_nifti = MinioOperator(
    dag=dag,
    name="minio-actions-put-nifti",
    action="put",
    batch_input_operators=[dcm2nifti],
    minio_prefix="downloads",
    whitelisted_file_extensions=(".zip", ".nii.gz"),
)
put_to_minio_dicom = MinioOperator(
    dag=dag,
    name="minio-actions-put-dicom",
    action="put",
    batch_input_operators=[get_input],
    minio_prefix="downloads",
    whitelisted_file_extensions=(".zip", ".dcm"),
)
clean = LocalWorkflowCleanerOperator(
    dag=dag, clean_workflow_dir=True, trigger_rule="none_failed_or_skipped"
)

get_input >> branch_if_nifti >> [dcm2nifti, put_to_minio_dicom]
dcm2nifti >> put_to_minio_nifti >> clean
put_to_minio_dicom >> clean
