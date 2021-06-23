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

trigger_dict_path = join(dirname(realpath(__file__)), "trigger_dict.json")
with open(trigger_dict_path, "r") as f:
    trigger_dict = json.load(f)

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
    incoming_modality = str(incoming_dcm[0x0008, 0x0060].value).lower()
    print("# Check Triggering from trigger_dict...")
    print("#")
    print(f"# Incoming-Modality: {incoming_modality}")
    print("#")
    for dcm_tag, config_list in trigger_dict.items():
        for config_entry in config_list:
            searched_values = [str(each_value).lower() for each_value in config_entry["searched_values"]]
            searched_modality = [str(each_value).lower() for each_value in config_entry["modality"]] if "modality" in config_entry else None

            print("#")
            print(f"# dcm_tag: {dcm_tag}")
            print(f"# dag_ids: {config_entry['dag_ids']}")
            print(f"# dcm_dataset:     {dcm_dataset}")
            print(f"# searched_values:   {searched_values}")
            print(f"# searched_modality: {searched_modality}")
            print("#")
            if dcm_tag == "all":
                for dag_id, conf in config_entry["dag_ids"].items():
                    print("# Triggering 'all'")
                    if dag_id == "service-extract-metadata" or (dcm_dataset != "dicom-test" and dcm_dataset != "phantom-example"):
                        trigger_it(dag_id=dag_id, dcm_path=dcm_path, series_uid=series_uid, conf=conf)
            
            elif dcm_dataset == "dicom-test" or dcm_dataset == "phantom-example":
                continue
            
            elif dcm_tag == "dataset" and dcm_dataset in searched_values and (searched_modality is None or incoming_modality in searched_modality):
                print(f"# Trigger because of dataset-match: {dcm_dataset}")
                for dag_id, conf in config_entry["dag_ids"].items():
                    trigger_it(dag_id=dag_id, dcm_path=dcm_path, series_uid=series_uid, conf=conf)

            elif dcm_tag in incoming_dcm and str(incoming_dcm[dcm_tag]).lower() in searched_values and (searched_modality is None or incoming_modality in searched_modality):
                for dag_id, conf, in config_entry["dag_ids"].items():
                    print("# Triggering dcm_tag -> '{dcm_tag}'")
                    trigger_it(dag_id=dag_id, dcm_path=dcm_path, series_uid=series_uid, conf=conf)
            print("#")

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
