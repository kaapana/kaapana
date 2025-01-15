from airflow.models import DAG
from datetime import timedelta
import pydicom
from shutil import copyfile
from airflow.utils.dates import days_ago
from kaapana.blueprints.kaapana_global_variables import AIRFLOW_WORKFLOW_DIR, BATCH_NAME
from kaapana.operators.LocalWorkflowCleanerOperator import LocalWorkflowCleanerOperator
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalDcm2JsonOperator import LocalDcm2JsonOperator
from kaapana.operators.LocalAddToDatasetOperator import LocalAddToDatasetOperator
from kaapana.operators.LocalJson2MetaOperator import LocalJson2MetaOperator


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


def start_reindexing(ds, **kwargs):
    import os
    import glob

    pacs_data_dir = "/kaapana/mounted/pacsdata"
    print("Start re-index")

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
        dcm_file = os.path.join(dcm_dir, os.listdir(dcm_dir)[0])
        print("DIR: {}".format(dcm_dir))
        print("dcm-file: {}".format(dcm_file))
        incoming_dcm = pydicom.dcmread(dcm_file)
        seriesUID = incoming_dcm.SeriesInstanceUID

        target_dir = os.path.join(
            AIRFLOW_WORKFLOW_DIR,
            dag_run_id,
            BATCH_NAME,
            "{}".format(seriesUID),
            "copy-from-pacs",
        )
        print(target_dir)

        if not os.path.exists(target_dir):
            os.makedirs(target_dir)

        copyfile(
            dcm_file, os.path.join(target_dir, os.path.basename(dcm_file) + ".dcm")
        )


copy_from_pacs = KaapanaPythonBaseOperator(
    name="copy-from-pacs",
    pool="default_pool",
    pool_slots=1,
    python_callable=start_reindexing,
    dag=dag,
)

extract_metadata = LocalDcm2JsonOperator(dag=dag, input_operator=copy_from_pacs)
add_to_dataset = LocalAddToDatasetOperator(dag=dag, input_operator=extract_metadata)
push_json = LocalJson2MetaOperator(
    dag=dag, input_operator=copy_from_pacs, json_operator=extract_metadata
)

clean = LocalWorkflowCleanerOperator(dag=dag, clean_workflow_dir=True)

copy_from_pacs >> extract_metadata >> add_to_dataset >> push_json >> clean
