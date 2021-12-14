from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
from kaapana.blueprints.kaapana_utils import generate_run_id
from airflow.models import DagBag
from glob import glob
from os.path import join, exists, basename, dirname, realpath
import os
import json
import shutil
import pydicom
from pathlib import Path


class LocalAutoTriggerOperator(KaapanaPythonBaseOperator):
    def trigger_it(self, dag_id, dcm_path, series_uid, conf={}):
        print("#")
        print(f"# Triggering dag-id: {dag_id}")
        print(f"# conf: {conf}")
        print("#")
        dag_run_id = generate_run_id(dag_id)

        if "fetch_method" in conf and conf["fetch_method"].lower() == "copy":
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
        else:
            print(f"# Using PACS fetch-method !")
            conf["inputs"] = {
                "dcm-uid": {
                    "study-uid": None,
                    "series-uid": series_uid,
                }
            }

        print(f"# conf: {conf}")
        trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)
        print(f"# Triggered! ")

    def start(self, ds, **kwargs):
        print("# ")
        print("# Starting LocalAutoTriggerOperator...")
        print("# ")
        print(kwargs)

        trigger_list = []
        for filePath in glob("/root/airflow/**/*trigger_rule.json"):
            with open(filePath, "r") as f:
                print(f"Found auto-trigger configuration: {filePath}")
                trigger_list = trigger_list + json.load(f)

        print("# ")
        print(f"# Found {len(trigger_list)} auto-trigger configurations -> start processing ...")
        print("# ")
        batch_folders = sorted([f for f in glob(join(WORKFLOW_DIR, kwargs['dag_run'].run_id, "batch", '*'))])
        for batch_element_dir in batch_folders:
            print("#")
            print(f"# Processing batch-element {batch_element_dir}")
            print("#")

            element_input_dir = join(batch_element_dir, self.operator_in_dir)

            # check if input dir present
            if not exists(element_input_dir):
                print("#")
                print(f"# Input-dir: {element_input_dir} does not exists!")
                print("# -> skipping")
                print("#")
                continue

            input_files = glob(join(element_input_dir, "*.dcm"), recursive=False)
            print(f"# Found {len(input_files)} input-files!")

            incoming_dcm = pydicom.dcmread(input_files[0])
            dcm_dataset = str(incoming_dcm[0x0012, 0x0020].value).lower() if (0x0012, 0x0020) in incoming_dcm else "N/A"
            series_uid = str(incoming_dcm[0x0020, 0x000E].value)

            print("#")
            print(f"# dcm_dataset:     {dcm_dataset}")
            print(f"# series_uid:      {series_uid}")
            print("#")

            for config_entry in trigger_list:
                fullfills_all_search_tags = True
                for search_key, search_value in config_entry["search_tags"].items():
                    dicom_tag = search_key.split(',')
                    if (dicom_tag in incoming_dcm) and (str(incoming_dcm[dicom_tag].value).lower() == search_value.lower()):
                        print(f"Filtering for {incoming_dcm[dicom_tag]}")
                    else:
                        fullfills_all_search_tags = False
                if fullfills_all_search_tags is True:
                    for dag_id, conf, in config_entry["dag_ids"].items():
                        if dag_id == "service-extract-metadata" or (dcm_dataset != "dicom-test" and dcm_dataset != "phantom-example"):
                            print(f"# Triggering '{dag_id}'")
                            self.trigger_it(dag_id=dag_id, dcm_path=element_input_dir, series_uid=series_uid, conf=conf)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="auto-dag-trigger",
            python_callable=self.start,
            **kwargs
        )
