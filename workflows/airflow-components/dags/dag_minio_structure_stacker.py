from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.utils.dates import days_ago
from datetime import timedelta
from airflow.models import DAG
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator
from mitk_minio_pacs_interaction.LocalFolderStructureConverterOperator import LocalFolderStructureConverterOperator

log = LoggingMixin().log
# finished


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
    dag_id='minio-structure-stacker',
    default_args=args,
    concurrency=20,
    max_active_runs=10,
    schedule_interval=None)


# example structure:
# bucket_name : pacs-dicom-data
#  dicom_db/
# ├── GebDat_PatientBirthDateTAG_Pseudo_PatientIDTAG
# │   └── StudyDescriptionTAG_StudyDateTAG
# │       ├── SeriesDescriptionTAG
#  segmentation_tree/
# ├── GebDat_PatientBirthDateTAG_Pseudo_PatientIDTAG
# │   └── StudyDescriptionTAG_StudyDateTAG
# │       ├── SeriesDescriptionTAG
# │           └── .keep  <- placeholder if empty_dir

bucket_name = "pacs-dicom-data"
folder_name = "dicom_db"
another_folder = "segmentation_tree" # this folder is used to create space to put created segmentations

structure = [{
    "value": [{"type": "string", "value": folder_name}],
    "children": {
        "value": [
            {"type": "string", "value": "GebDat"},
            {"type": "dicom_tag", "value": [0x0010, 0x0030]},  # PatientBirthDate
            {"type" : "string",  "value" : "Pseudo"},
            {"type": "dicom_tag", "value": [0x0010, 0x0020]}],  # PatientID
        "children": {
            "value": [
                {"type": "dicom_tag", "value":  [0x0008, 0x1030]},   # StudyDescription
                {"type": "dicom_tag",  "value": [0x0008, 0x0020]}],  # StudyDate
            "children": {
                "value": [{"type": "dicom_tag", "value": [0x0008, 0x103e]}],  # SeriesDescription
                "children": None}
        }
    }
},
    {
    "value": [{"type": "string", "value": another_folder}],
    "empty_dir": True,
    "children": {
        "value": [
            {"type": "string", "value": "GebDat"},
            {"type": "dicom_tag", "value": [0x0010, 0x0030]},  # PatientBirthDate
            {"type" : "string",  "value" : "Pseudo"},
            {"type": "dicom_tag", "value": [0x0010, 0x0020]}],  # PatientID
        "children": {
            "value": [
                {"type": "dicom_tag", "value":  [0x0008, 0x1030]},   # StudyDescription
                {"type": "dicom_tag",  "value": [0x0008, 0x0020]}],  # StudyDate
            "children": None}
    }
}]

get_input = LocalGetInputDataOperator(dag=dag)
structure_folder = LocalFolderStructureConverterOperator(dag=dag, structure=structure, input_operator=get_input)

push_to_minio = LocalMinioOperator(dag=dag,
                                   action='put',
                                   bucket_name= bucket_name,
                                   file_white_tuples=('.dcm','.keep'),
                                   zip_files=False)


clean = LocalWorkflowCleanerOperator(dag=dag)

get_input>> structure_folder >> push_to_minio >> clean
