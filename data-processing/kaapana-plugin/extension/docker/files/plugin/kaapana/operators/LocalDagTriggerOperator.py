from kaapana.operators.HelperMinio import HelperMinio
from kaapana.operators.HelperElasticsearch import HelperElasticsearch
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

from airflow.api.common.experimental.trigger_dag import trigger_dag as trigger
import os
import time
import errno
import json
import glob
import shutil
import pydicom
from datetime import timedelta
from pathlib import Path


class LocalDagTriggerOperator(KaapanaPythonBaseOperator):
    def check_cache(self, dicom_series, cache_operator):
        loaded_from_cache = True
        study_uid = dicom_series["dcm-uid"]["study-uid"]
        series_uid = dicom_series["dcm-uid"]["series-uid"]

        output_dir = os.path.join(self.run_dir, BATCH_NAME, series_uid, self.operator_out_dir)
        # ctpet-prep batch 1.3.12.2.1107.5.8.15.101314.30000019092314381173500002262normalization

        object_dirs = [os.path.join(BATCH_NAME, series_uid, cache_operator)]
        HelperMinio.apply_action_to_object_dirs(HelperMinio.minioClient, "get", self.target_bucket, output_dir,
                                                object_dirs=object_dirs)
        try:
            if len(os.listdir(output_dir)) == 0:
                loaded_from_cache = False
        except FileNotFoundError:
            loaded_from_cache = False

        if loaded_from_cache:
            print()
            print("✔ Chache data found for series: {}".format(dicom_series["dcm-uid"]["series-uid"]))
            print()
        else:
            print()
            print("✘ NO data found for series: {}".format(dicom_series["dcm-uid"]["series-uid"]))
            print()

        return loaded_from_cache

    def get_dicom_list(self):
        dicom_info_list = []

        if self.use_dcm_files:
            no_data_processed = True
            batch_folder = [f for f in glob.glob(os.path.join(self.run_dir, BATCH_NAME, '*'))]
            for batch_element_dir in batch_folder:
                input_dir = os.path.join(batch_element_dir, self.operator_in_dir)
                dcm_file_list = glob.glob(input_dir + "/*.dcm", recursive=True)
                if len(dcm_file_list) == 0:
                    print()
                    print("#############################################################")
                    print()
                    print("Couldn't find any DICOM file in dir: {}".format(input_dir))
                    print()
                    print("#############################################################")
                    print()
                    continue
                no_data_processed = False
                dicom_file = pydicom.dcmread(dcm_file_list[0])
                study_uid = dicom_file[0x0020, 0x000D].value
                series_uid = dicom_file[0x0020, 0x000E].value
                modality = dicom_file[0x0008, 0x0060].value
                if self.from_data_dir:
                    dicom_info_list.append(
                        {
                            "input-dir": input_dir,
                            "series-uid": series_uid
                        })
                else:
                    dicom_info_list.append(
                        {
                            "dcm-uid": {
                                "study-uid": study_uid,
                                "series-uid": series_uid,
                                "modality": modality
                            }
                        })
            if no_data_processed:
                print("No files processed in any batch folder!")
                raise ValueError('ERROR')
        else:
            if self.conf == None or not "inputs" in self.conf:
                print("No config or inputs in config found!")
                print("Abort.")
                raise ValueError('ERROR')
            inputs = self.conf["inputs"]
            if not isinstance(inputs, list):
                inputs = [inputs]

            for input in inputs:
                if "elastic-query" in input:
                    elastic_query = input["elastic-query"]
                    if "query" not in elastic_query:
                        print("'query' not found in 'elastic-query': {}".format(input))
                        print("abort...")
                        raise ValueError('ERROR')
                    if "index" not in elastic_query:
                        print("'index' not found in 'elastic-query': {}".format(input))
                        print("abort...")
                        raise ValueError('ERROR')

                    query = elastic_query["query"]
                    index = elastic_query["index"]

                    cohort = HelperElasticsearch.get_query_cohort(elastic_index=index, elastic_query=query)
                    for series in cohort:
                        series = series["_source"]
                        study_uid = series[HelperElasticsearch.study_uid_tag]
                        series_uid = series[HelperElasticsearch.series_uid_tag]
                        # SOPInstanceUID = series[ElasticDownloader.SOPInstanceUID_tag]
                        modality = series[HelperElasticsearch.modality_tag]
                        dicom_info_list.append(
                            {
                                "dcm-uid": {
                                    "study-uid": study_uid,
                                    "series-uid": series_uid,
                                    "modality": modality
                                }
                            }
                        )

                elif "dcm-uid" in input:
                    dcm_uid = input["dcm-uid"]

                    if "study-uid" not in dcm_uid:
                        print("'study-uid' not found in 'dcm-uid': {}".format(input))
                        print("abort...")
                        raise ValueError('ERROR')
                    if "series-uid" not in dcm_uid:
                        print("'series-uid' not found in 'dcm-uid': {}".format(input))
                        print("abort...")
                        raise ValueError('ERROR')

                    study_uid = dcm_uid["study-uid"]
                    series_uid = dcm_uid["series-uid"]
                    modality = dcm_uid["modality"]

                    dicom_info_list.append(
                        {
                            "dcm-uid": {
                                "study-uid": study_uid,
                                "series-uid": series_uid,
                                "modality": modality
                            }
                        }
                    )

                else:
                    print("Error with dag-config!")
                    print("Unknown input: {}".format(input))
                    print("Supported 'dcm-uid' and 'elastic-query' ")
                    print("Dag-conf: {}".format(self.conf))
                    raise ValueError('ERROR')

        return dicom_info_list

    def copy(self, src, target):
        print("src/dst:")
        print(src)
        print(target)

        try:
            shutil.copytree(src, target)
        except OSError as e:
            # If the error was caused because the source wasn't a directory
            if e.errno == errno.ENOTDIR:
                shutil.copy(src, target)
            else:
                print(('Directory not copied. Error: %s' % e))
                raise Exception('Directory not copied. Error: %s' % e)
                raise ValueError('ERROR')

    def trigger_dag(self, ds, **kwargs):
        pending_dags = []
        done_dags = []

        self.conf = kwargs['dag_run'].conf
        self.dag_run_id = kwargs['dag_run'].run_id
        self.run_dir = os.path.join(WORKFLOW_DIR, self.dag_run_id)
        dicom_info_list = self.get_dicom_list()
        trigger_series_list = []
        for dicom_series in dicom_info_list:
            if self.use_dcm_files:
                if self.from_data_dir:
                    break
                elif self.trigger_mode == "batch":
                    if len(trigger_series_list) == 0:
                        trigger_series_list.append([])
                    trigger_series_list[0].append(dicom_series)
                elif self.trigger_mode == "single":
                    trigger_series_list.append([dicom_series])
            else:
                for cache_operator in self.cache_operators:
                    cache_found = self.check_cache(dicom_series=dicom_series, cache_operator=cache_operator)
                    if not cache_found and self.trigger_mode == "batch":
                        if len(trigger_series_list) == 0:
                            trigger_series_list.append([])
                        trigger_series_list[0].append(dicom_series)
                    elif not cache_found and self.trigger_mode == "single":
                        trigger_series_list.append([dicom_series])
                    elif not cache_found:
                        print()
                        print("#############################################################")
                        print()
                        print("TRIGGER_MODE: {} is not supported!".format(self.trigger_mode))
                        print("Please use: 'single' or 'batch' -> abort.")
                        print()
                        print("#############################################################")
                        print()
                        raise ValueError('ERROR')

        print()
        print("#############################################################")
        print()
        print("TRIGGER-LIST: ")
        print(json.dumps(trigger_series_list, indent=4, sort_keys=True))
        print()
        print("#############################################################")
        print()

        # trigger current workflow data 
        if self.use_dcm_files and self.from_data_dir:
            dag_run_id = generate_run_id(self.trigger_dag_id)
            target_list = set()
            for dicom_series in dicom_info_list:
                src = dicom_series["input-dir"]
                target_dir = self.operator_out_dir if self.operator_out_dir else "get-input-data"
                target = os.path.join(self.workflow_dir, dag_run_id, self.batch_name, dicom_series["series-uid"],
                                      target_dir)
                target_list.add(target)
                self.copy(src, target)
            self.conf["dataInputDirs"] = list(target_list)
            trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=self.conf,
                                    replace_microseconds=False)

        for element in trigger_series_list:
            conf = {
                "inputs": element,
                **self.conf
                # "conf": self.conf
            }
            dag_run_id = generate_run_id(self.trigger_dag_id)
            triggered_dag = trigger(dag_id=self.trigger_dag_id, run_id=dag_run_id, conf=conf,
                                    replace_microseconds=False)
            pending_dags.append(triggered_dag)

        while self.wait_till_done and len(pending_dags) > 0:
            print("Some triggered DAGs are still pending -> waiting {} s".format(self.delay))
            for pending_dag in list(pending_dags):
                pending_dag.update_state()
                state = pending_dag.get_state()
                if state == "running":
                    continue
                elif state == "success":
                    done_dags.append(pending_dag)
                    pending_dags.remove(pending_dag)
                    for series in pending_dag.conf["inputs"]:
                        for cache_operator in self.cache_operators:
                            if not self.check_cache(dicom_series=series, cache_operator=cache_operator):
                                print()
                                print("#############################################################")
                                print()
                                print("Could still not find the data after the sub-dag.")
                                print("This is unexpected behaviour -> error")
                                print()
                                print("#############################################################")
                                raise ValueError('ERROR')

                elif state == "failed":
                    print()
                    print("#############################################################")
                    print()
                    print("Triggered Dag Failed: {}".format(pending_dag.id))
                    print()
                    print("#############################################################")
                    print()
                    raise ValueError('ERROR')
                else:
                    print()
                    print("#############################################################")
                    print()
                    print("Unknown DAG-state!")
                    print("DAG:   {}".format(pending_dag.id))
                    print("STATE: {}".format(state))
                    print()
                    print("#############################################################")
                    print()
                    raise ValueError('ERROR')

            time.sleep(self.delay)

        print()
        print("#############################################################")
        print()
        print("#######################  DONE  ##############################")
        print()
        print("#############################################################")
        print()

    def __init__(self,
                 dag,
                 trigger_dag_id,
                 cache_operators=[],
                 target_bucket=None,
                 trigger_mode="single",
                 wait_till_done=False,
                 use_dcm_files=True,
                 from_data_dir=False,
                 delay=10,
                 **kwargs):

        self.trigger_dag_id = trigger_dag_id
        self.wait_till_done = wait_till_done
        self.trigger_mode = trigger_mode.lower()
        self.cache_operators = cache_operators if isinstance(cache_operators, list) else [cache_operators]
        self.target_bucket = target_bucket
        self.use_dcm_files = use_dcm_files
        self.from_data_dir = from_data_dir
        self.delay = delay

        name = "trigger_" + self.trigger_dag_id

        super(LocalDagTriggerOperator, self).__init__(
            dag=dag,
            name=name,
            python_callable=self.trigger_dag,
            execution_timeout=timedelta(minutes=180),
            **kwargs)
