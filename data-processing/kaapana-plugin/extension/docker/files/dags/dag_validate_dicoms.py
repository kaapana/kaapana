import glob
import json
import os
from datetime import timedelta
from pathlib import Path
from pprint import pprint

import pydicom
from airflow.models import DAG
from airflow.operators.python import BranchPythonOperator
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago
from airflow.utils.log.logging_mixin import LoggingMixin
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.DcmValidatorOperator import DcmValidatorOperator
from kaapana.operators.GetInputOperator import GetInputOperator
from kaapana.operators.LocalClearValidationResultOperator import (
    LocalClearValidationResultOperator,
)
from kaapana.operators.LocalMinioOperator import LocalMinioOperator
from kaapana.operators.LocalValidationResult2MetaOperator import (
    LocalValidationResult2MetaOperator,
)
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapanapy.helper.HelperOpensearch import HelperOpensearch

ui_forms = {
    "workflow_form": {
        "type": "object",
        "properties": {
            "validator_algorithm": {
                "title": "Validator Algorithm",
                "description": "Choose the algorithm to validate your dicoms",
                "enum": ["dicom-validator", "dciodvfy"],
                "type": "string",
                "default": "dicom-validator",
                "required": True,
            },
            "exit_on_error": {
                "title": "Stop execution on Validation Error",
                "description": "Validator will raise an error and stop executing on validation fail if set to True",
                "type": "boolean",
                "default": False,
            },
            "tags_whitelist": {
                "type": "array",
                "title": "Tags Whitelist",
                "description": "List of DICOM tags, that will be ignored while validating",
                "items": {"type": "string", "title": "DICOM tag"},
                "default": [],
            },
        },
    }
}

log = LoggingMixin().log

args = {
    "ui_forms": ui_forms,
    "ui_visible": True,
    "owner": "kaapana",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=30),
    "depends_on_past": False,
}

dag = DAG(dag_id="validate-dicoms", default_args=args, schedule_interval=None)


def get_series_metadata(dcmfile: pydicom.Dataset):
    target_tags = [
        HelperOpensearch.study_uid_tag,
        HelperOpensearch.series_uid_tag,
        HelperOpensearch.SOPInstanceUID_tag,
        HelperOpensearch.modality_tag,
        HelperOpensearch.protocol_name,
        HelperOpensearch.curated_modality_tag,
        "00080016 SOPClassUID_keyword",
        "00080020 StudyDate_date",
        "00080030 StudyTime_time",
        "00080050 AccessionNumber_keyword",
        "00080064 ConversionType_keyword",
        "00100010 PatientName_keyword_alphabetic",
        "00100020 PatientID_keyword",
        "00100040 PatientSex_keyword",
        "00102180 Occupation_keyword",
        "00104000 PatientComments_keyword",
    ]
    ds = pydicom.dcmread(dcmfile)
    series_metadata = {}

    for tag in target_tags:
        dicomtag = tag.split(" ")[1]
        dicomtag = dicomtag.split("_")[0]
        tagvalue = ds.get(dicomtag, "")
        if tagvalue != "":
            series_metadata[tag] = str(tagvalue)

    return series_metadata


def create_input_json_from_input(ds, **kwargs):
    batch_dir = Path(AIRFLOW_WORKFLOW_DIR) / kwargs["dag_run"].run_id / BATCH_NAME

    batch_folder = [f for f in glob.glob(os.path.join(batch_dir, "*"))]

    for batch_element_dir in batch_folder:
        input_dir = Path(batch_element_dir) / get_input.operator_out_dir
        output_dir = Path(batch_element_dir) / get_input_json.operator_out_dir
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
            continue

        metadata = get_series_metadata(dcms[0])

        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        json_path = os.path.join(output_dir, "metadata.json")
        with open(json_path, "w") as fp:
            json.dump(metadata, fp, indent=4, sort_keys=True)
        print("Mendatory metadata file created one series metadata only")
    return


def fetch_input_json_callable(**kwargs):
    conf = kwargs["dag_run"].conf
    if "data_form" in conf and "identifiers" in conf["data_form"]:
        return [get_input_json.name]
    else:
        return [get_input_json_from_input_files.task_id]


get_input = GetInputOperator(dag=dag)

validate = DcmValidatorOperator(
    dag=dag,
    input_operator=get_input,
    exit_on_error=False,
)

get_input_json = GetInputOperator(
    dag=dag,
    name="get-json-input-data",
    data_type="json",
)

get_input_json_from_input_files = PythonOperator(
    task_id="get-json-input-data-from-input",
    provide_context=True,
    pool="default_pool",
    executor_config={"cpu_millicores": 100, "ram_mem_mb": 50},
    python_callable=create_input_json_from_input,
    dag=dag,
)

branching_get_input_json = BranchPythonOperator(
    task_id="branching-get-input-json",
    provide_context=True,
    python_callable=fetch_input_json_callable,
    trigger_rule="none_failed_min_one_success",
    dag=dag,
)

clear_validation_results = LocalClearValidationResultOperator(
    dag=dag,
    name="clear-validation-results",
    input_operator=get_input_json,
    result_bucket="staticwebsiteresults",
    trigger_rule="none_failed_min_one_success",
)

save_to_meta = LocalValidationResult2MetaOperator(
    dag=dag,
    input_operator=get_input_json,
    validator_output_dir=validate.operator_out_dir,
    validation_tag="00111001",
)

put_html_to_minio = LocalMinioOperator(
    dag=dag,
    action_operator_dirs=[validate.operator_out_dir],
    name="put-results-html-to-minio",
    action="put",
    bucket_name="staticwebsiteresults",
    file_white_tuples=(".html"),
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)


get_input >> validate >> branching_get_input_json
branching_get_input_json >> get_input_json >> clear_validation_results
branching_get_input_json >> get_input_json_from_input_files >> clear_validation_results
clear_validation_results >> save_to_meta >> put_html_to_minio >> clean
