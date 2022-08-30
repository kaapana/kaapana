from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from airflow.api.common.trigger_dag import trigger_dag as trigger
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
    """
        Operator to trigger workflows from within a workflow.
        To automatically trigger workflows configuration JSON files with the name */*trigger_rule.json* are needed.
        The operator search for all files with this extension in the dags folder.

        **Inputs:**

        JSON file example:
       [
          {
             "search_tags": {},
             "dag_ids": {
                   <dag id to trigger>: {
                      "fetch_method": "copy",
                      "single_execution" : false
                   }
             }
          }
       ]

        **Outputs:**

        * all workflows with predefined trigger rules are triggered
        """

    def trigger_it(self, triggering):
        dag_id = triggering["dag_id"]
        dag_run_id = triggering["dag_run_id"]
        conf = triggering["conf"]
        print("#")
        print(f"# Triggering dag-id: {dag_id}")
        print(f"# Dag run id: '{dag_run_id}'")
        print(f"# conf: {conf}")
        print("#")
        trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)
        print(f"# Triggered! ")

    def set_data_input(self, dag_id, dcm_path, dag_run_id, series_uid, conf={}):
        print("Set input data")
        print(f"# conf: {conf}")
        print("#")
        if "fetch_method" in conf and conf["fetch_method"].lower() == "copy":
            print("# Searching DAG-id in DagBag:")
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
                    break
        else:
            print(f"# Using PACS fetch-method !")
            if "inputs" not in conf:
                conf["inputs"] = []
            conf["inputs"].append({
                "dcm-uid": {
                    "study-uid": None,
                    "series-uid": series_uid,
                }
            })

        return conf

    def start(self, ds, **kwargs):
        print("# ")
        print("# Starting LocalAutoTriggerOperator...")
        print("# ")
        print(kwargs)
        trigger_rule_list = []
        for filePath in glob("/root/airflow/**/*trigger_rule.json"):
            with open(filePath, "r") as f:
                print(f"Found auto-trigger configuration: {filePath}")
                trigger_rule_list = trigger_rule_list + json.load(f)

        print("# ")
        print(f"# Found {len(trigger_rule_list)} auto-trigger configurations -> start processing ...")
        print("# ")

        batch_folders = sorted([f for f in glob(join(WORKFLOW_DIR, kwargs['dag_run'].run_id, "batch", '*'))])
        triggering_list = []
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

            for config_entry in trigger_rule_list:
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
                            single_execution = False
                            if "single_execution" in conf and conf["single_execution"]:
                                # if it is a batch, still process triggered dag witout batch-processing
                                print("Single execution enabled for dag!")
                                single_execution = True
                            if single_execution:
                                dag_run_id = generate_run_id(dag_id)
                            else:
                                dag_run_id = ""
                                for triggering in triggering_list:
                                    if dag_id == triggering["dag_id"]:
                                        dag_run_id = triggering["dag_run_id"]
                                        conf = triggering["conf"]
                                        break
                                if not dag_run_id:
                                    dag_run_id = generate_run_id(dag_id)
                            conf = self.set_data_input(dag_id=dag_id,
                                                       dcm_path=element_input_dir,
                                                       dag_run_id=dag_run_id,
                                                       series_uid=series_uid,
                                                       conf=conf)
                            if not single_execution:
                                for i in range(len(triggering_list)):
                                    if triggering_list[i]['dag_id'] == dag_id:
                                        del triggering_list[i]
                                        break

                            triggering_list.append({
                                "dag_id": dag_id,
                                "conf": conf,
                                "dag_run_id": dag_run_id
                            })

        for triggering in triggering_list:
            self.trigger_it(triggering)

    def __init__(self,
                 dag,
                 **kwargs):

        super().__init__(
            dag=dag,
            name="auto-dag-trigger",
            python_callable=self.start,
            **kwargs
        )
