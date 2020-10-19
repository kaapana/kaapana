from airflow.operators.python_operator import PythonOperator
from airflow.models import DAG
from datetime import timedelta
from airflow.utils.dates import days_ago
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.LocalCtpQuarantineCheckOperator import LocalCtpQuarantineCheckOperator

args = {
    'ui_visible': False,
    'owner': 'kaapana',
    'start_date': days_ago(0),
    'retries': 1,
    'retry_delay': timedelta(seconds=60)
}


dag = DAG(
    dag_id='process_incoming_dcm',
    default_args=args,
    schedule_interval=None,
    concurrency=50,
    max_active_runs=50
)


def process_incoming(ds, **kwargs):
    import shutil
    import errno
    import pydicom
    import glob
    import json
    import time
    import os
    import logging
    import traceback
    import uuid

    from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger

    def check_all_files_arrived(dcm_path):
        if not os.path.isdir(dcm_path):
            print("Could not find dicom dir!")
            print("Exiting")
            exit(1)

        dcm_files = sorted(glob.glob(dcm_path+"/*.dcm*"))
        return dcm_files

    def trigger_it(dag_id, dcm_path, series_uid):
        dag_run_id = generate_run_id(dag_id)

        target = os.path.join("/data", dag_run_id, "batch", series_uid, "initial-input")
        print("MOVE!")
        print("SRC: {}".format(dcm_path))
        print("TARGET: {}".format(target))
        shutil.move(dcm_path, target)

        print(("TRIGGERING! DAG-ID: %s RUN_ID: %s" % (dag_id, dag_run_id)))
        trigger(dag_id=dag_id, run_id=dag_run_id, replace_microseconds=False)

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
    # @all images
    trigger_it(dag_id="extract-metadata",
               dcm_path=dcm_path, series_uid=series_uid)
    try:
        print(("SeriesDescription: %s" % incoming_dcm.SeriesDescription))
        print(("StudyDescription: %s" % incoming_dcm.StudyDescription))

        # if incoming_dcm.SeriesDescription == "Abdomen pv 3.0  B31f DE mint  F_0.5" or incoming_dcm.SeriesDescription == "Abdomen pv  3.0  B31f":
        #     trigger_it(dag_id="organ_segmentation",
        #                 dcm_path=dcm_path, series_uid=series_uid)

        # if "head" in incoming_dcm.StudyDescription.lower() or "kopf" in incoming_dcm.StudyDescription.lower():
        #     trigger_it(dag_id="brain_extraction", dcm_path=dcm_path)
    except Exception as e:
        print("ERROR!")
        logging.error(traceback.format_exc())

    import shutil
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
