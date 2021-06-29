from airflow.operators.python_operator import PythonOperator
from airflow.models import DAG, DagBag
from datetime import timedelta
from airflow.utils.dates import days_ago
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.LocalCtpQuarantineCheckOperator import LocalCtpQuarantineCheckOperator
import json
from os.path import realpath, join, basename, dirname
import os
import shutil
import pydicom
import glob

trigger_list = []
for filePath in glob.glob("/root/airflow/**/*trigger_rule.json"):
    with open(filePath,"r") as f:
        print(filePath)
        trigger_list = trigger_list + json.load(f)

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}

dag = DAG(
    dag_id='service-process-incoming-dcm',
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=50
)


def process_incoming(ds, **kwargs):
    from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger

    def check_all_files_arrived(dcm_path):
        if not os.path.isdir(dcm_path):
            print("Could not find dicom dir!")
            print("Exiting")
            exit(1)

        dcm_files = sorted(glob.glob(dcm_path+"/*.dcm*"))
        return dcm_files

    def trigger_it(dag_id, dcm_path, series_uid, conf={}):
        print("#")
        print(f"# Triggering dag-id: {dag_id}")
        print(f"# conf: {conf}")
        print("#")
        dag_run_id = generate_run_id(dag_id)
        
        print("# Searching DAG-id in DagBag:")
        get_input_dir_name = None
        for dag in DagBag().dags.values():
            if dag.dag_id == dag_id:
                print(f"# found dag_id: {dag.dag_id}")
                for task in dag.tasks:
                    if "LocalGetInputDataOperator" == task.__class__.__name__:
                        print(f"# found LocalGetInputDataOperator task: {task.name}")
                        get_input_dir_name = task.operator_out_dir
                        target = os.path.join("/data", dag_run_id, "batch", series_uid, get_input_dir_name)
                        print(f"# Copy data to: {target}")
                        shutil.copytree(src=dcm_path, dst=target)
                        print("#")
                        break

        trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)

    dicom_path = kwargs['dag_run'].conf.get('dicom_path')
    patient_id = kwargs['dag_run'].conf.get('patientID')
    study_id = kwargs['dag_run'].conf.get('studyInstanceUID')
    series_uid = kwargs['dag_run'].conf.get('seriesInstanceUID')
    callingAET = kwargs['dag_run'].conf.get('callingAET')
    calledAET = kwargs['dag_run'].conf.get('calledAET')

    dcm_path = os.path.join("/ctpinput", dicom_path)
    print(("Dicom-path: %s" % dcm_path))

    dcm_files = check_all_files_arrived(dcm_path)
    incoming_dcm = pydicom.dcmread(dcm_files[0])
    dcm_dataset = str(incoming_dcm[0x0012, 0x0020].value).lower() if (0x0012, 0x0020) in incoming_dcm else "N/A"

    print(f"# dcm_dataset:     {dcm_dataset}")


    for config_entry in trigger_list:
        fullfills_all_search_tags = True
        for search_key, search_value in config_entry["search_tags"].items():
            dicom_tag = search_key.split(',')
            if (dicom_tag in incoming_dcm) and (str(incoming_dcm[dicom_tag].value).lower() == search_value.lower()):
                print(f"Filtering for {incoming_dcm[dicom_tag]}")
            else:
                fullfills_all_search_tags = False        
        if  fullfills_all_search_tags is True:
            for dag_id, conf, in config_entry["dag_ids"].items():
                if dag_id == "service-extract-metadata" or (dcm_dataset != "dicom-test" and dcm_dataset != "phantom-example"):
                    print(f"# Triggering '{dag_id}'")
                    trigger_it(dag_id=dag_id, dcm_path=dcm_path, series_uid=series_uid, conf=conf)
                
    print(("Deleting temp data: %s" % dcm_path))
    shutil.rmtree(dcm_path, ignore_errors=True)


run_this = PythonOperator(
    task_id='trigger_dags',
    provide_context=True,
    pool='default_pool',
    executor_config={
        "cpu_millicores": 100,
        "ram_mem_mb": 50,
        "gpu_mem_mb": 0
    },
    python_callable=process_incoming,
    dag=dag)

check_ctp = LocalCtpQuarantineCheckOperator(dag=dag)

run_this >> check_ctp
