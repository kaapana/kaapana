from airflow.models import DAG
from datetime import timedelta
import pydicom
from pydicom.tag import Tag
import json
import os
import glob
from airflow.utils.dates import days_ago
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator
from kaapana.operators.LocalAssignDataToProjectOperator import (
    LocalAssignDataToProjectOperator,
)

args = {
    "ui_visible": False,
    "owner": "system",
    "start_date": days_ago(0),
    "retries": 0,
    "retry_delay": timedelta(seconds=10),
}

dag = DAG(
    dag_id="service-re-index-dicom-data",
    default_args=args,
    schedule_interval=None,
    concurrency=1,
    max_active_runs=1,
    tags=["service"],
)


def _delete_pixel_data(dcm: pydicom.Dataset) -> pydicom.Dataset:
    """Remove pixel data elements to reduce memory usage"""
    # (0014,3080) Bad Pixel Image
    # (7FE0,0008) Float Pixel Data
    # (7FE0,0009) Double Float Pixel Data
    # (7FE0,0010) Pixel Data
    pixel_data_elements = [
        (0x0014, 0x3080),
        (0x7FE0, 0x0008),
        (0x7FE0, 0x0009),
        (0x7FE0, 0x0010),
    ]
    for elem in pixel_data_elements:
        tag = Tag(*elem)
        if tag in dcm:
            del dcm[tag]
    return dcm


def start_reindexing_optimized(ds, **kwargs):
    """Optimized reindexing that creates JSON metadata without copying DICOM files"""
    pacs_data_dir = "/kaapana/mounted/pacsdata"
    print("Start optimized re-index")

    dcm_dirs = []
    file_list = glob.glob(pacs_data_dir + "/fs1/**/*", recursive=True)
    for fi in file_list:
        if os.path.isfile(fi):
            dcm_dirs.append(os.path.dirname(fi))
    dcm_dirs = list(set(dcm_dirs))

    print("Files found: {}".format(len(file_list)))
    print("Dcm dirs found: {}".format(len(dcm_dirs)))
    dag_run_id = kwargs["dag_run"].run_id
    print("Run-id: {}".format(dag_run_id))

    for dcm_dir in dcm_dirs:
        try:
            dcm_file = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])
            print("DIR: {}".format(dcm_dir))
            print("dcm-file: {}".format(dcm_file))

            dcm = pydicom.dcmread(dcm_file, stop_before_pixels=True)

            # Remove any remaining pixel data elements
            dcm = _delete_pixel_data(dcm)

            # Get series UID for directory structure
            seriesUID = dcm.SeriesInstanceUID

            # Create target directory structure
            target_dir = os.path.join(
                AIRFLOW_WORKFLOW_DIR,
                dag_run_id,
                BATCH_NAME,
                "{}".format(seriesUID),
                "extract-metadata-direct",
            )

            print(target_dir)

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            json_dict = dcm.to_json_dict()

            del dcm

            json_filename = os.path.basename(dcm_file) + ".json"
            json_path = os.path.join(target_dir, json_filename)

            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(json_dict, f, indent=2, ensure_ascii=False)

            print("Saved JSON metadata to: {}".format(json_path))

        except Exception as e:
            print("Error processing directory {}: {}".format(dcm_dir, str(e)))
            continue

    print("Re-indexing completed")


extract_metadata_direct = KaapanaPythonBaseOperator(
    name="extract-metadata-direct",
    pool="default_pool",
    pool_slots=1,
    python_callable=start_reindexing_optimized,
    dag=dag,
)


# add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata_direct)

extract_metadata = LocalDcm2JsonOperator(
    dag=dag, input_operator=extract_metadata_direct, data_type="json"
)
push_json = LocalJson2MetaOperator(dag=dag, json_operator=extract_metadata)

assign_to_project = LocalAssignDataToProjectOperator(
    dag=dag, input_operator=extract_metadata
)
# clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

# Updated task dependencies
(
    extract_metadata_direct
    >> extract_metadata
    >> (assign_to_project, push_json)
    # >> (add_to_dataset, assign_to_project, push_json)
    # >> clean
)
