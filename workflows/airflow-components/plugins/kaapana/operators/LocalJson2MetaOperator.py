import shutil
import os
import json
import elasticsearch
import elasticsearch.helpers
from datetime import datetime
import glob
import traceback
import logging
import pydicom
import errno
import time
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR

class LocalJson2MetaOperator(KaapanaPythonBaseOperator):

    def start(self, ds, **kwargs):
        global es

        self.ti = kwargs['ti']
        print("Starting module json2elastic")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        if self.dicom_operator is not None:
            self.rel_dicom_dir = self.dicom_operator.operator_out_dir
        else:
            self.rel_dicom_dir = self.operator_in_dir

        self.run_id = kwargs['dag_run'].run_id
        print(("RUN_ID: %s" % self.run_id))

        es = elasticsearch.Elasticsearch([{'host': self.elastic_host, 'port': self.elastic_port}])

        for batch_element_dir in batch_folder:

            if self.jsonl_operator:
                #jsonl_dir = os.path.join(batch_element_dir, self.jsonl_operator.operator_out_dir)
                jsonl_dir = os.path.join(batch_element_dir, self.jsonl_operator.operator_out_dir)
                jsonl_list = glob.glob(jsonl_dir+'/**/*.jsonl', recursive=True)
                for jsonl_file in jsonl_list:
                    print(("Pushing file: %s to elasticsearch!" % jsonl_file))
                    with open(jsonl_file, encoding='utf-8') as f:
                        for line in f:
                            obj = json.loads(line)
                            self.push_json(obj)
            else:
                # TODO: is this dcm check neccesary? InstanceID is set in upload
                dcm_files = sorted(glob.glob(os.path.join(batch_element_dir, self.rel_dicom_dir, "*.dcm*"), recursive=True))
                self.get_id(dcm_files[0])

                json_dir = os.path.join(batch_element_dir, self.json_operator.operator_out_dir)
                print(("Pushing json files from: %s" % json_dir))
                json_list = glob.glob(json_dir+'/**/*.json', recursive=True)
                print(("Found json files: %s" % len(json_list)))

                for json_file in json_list:
                    print(("Pushing file: %s to elasticsearch!" % json_file))
                    with open(json_file, encoding='utf-8') as f:
                        new_json = json.load(f)
                    self.push_json(new_json)

    def mkdir_p(self, path):
        try:
            os.makedirs(path)
        except OSError as exc:  # Python >2.5
            if exc.errno == errno.EEXIST and os.path.isdir(path):
                pass
            else:
                raise

    def get_id(self, dcm_file=None):
        if dcm_file is not None:
            self.instanceUID = pydicom.dcmread(dcm_file)[0x0020, 0x000e].value
            self.patient_id = pydicom.dcmread(dcm_file)[0x0010, 0x0020].value
            print(("Dicom instanceUID: %s" % self.instanceUID))
            print(("Dicom Patient ID: %s" % self.patient_id))
        elif self.set_dag_id:
            self.instanceUID = self.run_id
        else:
            print("dicom_operator and dct_to_push not specified!")

    def push_json(self, json_dict):
        global es
        if (es.indices.exists(self.elastic_index)):
            try:
                print(("Index", self.elastic_index, "exists, producing inserts and streaming them into ES."))
                for ok, item in elasticsearch.helpers.streaming_bulk(es, self.produce_inserts(json_dict), chunk_size=500, raise_on_error=True):
                    print(("status: %s" % item['index']['result']))
                    if not ok:
                        print(("appendJsonToIndex(): %s Item: %s" % (ok, item)))
            except Exception as e:
                print("######################################################################################################### ERROR IN TRANSMISSION!")
                logging.error(traceback.format_exc())
                print("#######################################  ERROR: %s")
                for err_msg in e.args:
                    print(err_msg)

                print("ERROR @PUSH FILE TO ELASTIC")
                exit(1)
        else:
            print("INDEX NOT EXISTING!")

    # def update_document(self, new_json):
    #     global elastic_indexname
    #     doc_id = self.instanceUID
    #     try:
    #         old_json = es.get(index=elastic_indexname,
    #                           doc_type="_doc", id=doc_id)["_source"]
    #     except Exception as e:
    #         print("doc is not updated! -> not found in es")
    #         old_json = {}

    #     for new_key in new_json:
    #         new_value = new_json[new_key]
    #         old_json[new_key] = new_value

    #     return old_json


    def check_pacs_availability(self, instanceUID: str):
        print("#")
        print("# Checking if series available in PACS...")
        check_count = 0
        while not HelperDcmWeb.checkIfSeriesAvailable(seriesUID=instanceUID):
            print("#")
            print(f"# Series {instanceUID} not found in PACS-> try: {check_count}")
            if check_count >= self.avalability_check_max_tries:
                print(f"# check_count >= avalability_check_max_tries {self.avalability_check_max_tries}")
                print("# Error! ")
                print("#")
                exit(1)

            print(f"# -> waiting {self.avalability_check_delay} s")
            time.sleep(self.avalability_check_delay)
            check_count += 1

    def produce_inserts(self, new_json):
        global es
        

        if self.check_in_pacs:
            self.check_pacs_availability(self.instanceUID)

        global elastic_indexname

        try:
            old_json = es.get(index=self.elastic_index, doc_type="_doc", id=self.instanceUID)["_source"]
            print("Series already found in ES")
            if self.no_update:
                exit(1)
        except Exception as e:
            print("doc is not updated! -> not found in es")
            print(e)
            old_json = {}

        bpr_key = "predicted_bodypart_string"
        for new_key in new_json:
            if new_key == bpr_key and bpr_key in old_json and old_json[bpr_key].lower() != "n/a":
                continue
            new_value = new_json[new_key]
            old_json[new_key] = new_value

        index = self.elastic_index

        try:

            doc = {}
            doc["_id"] = self.instanceUID
            doc["_index"] = index
            doc["_type"] = "_doc"
            doc["_source"] = old_json

            yield doc
        except (KeyError) as e:
            print(('KeyError in produce_inserts():', e, ', from input line: ', line[line.find('InstanceUID')-32:line.find('InstanceUID')+172]))
            pass

    def __init__(self,
                 dag,
                 dicom_operator=None,
                 json_operator=None,
                 jsonl_operator=None,
                 set_dag_id=False,
                 no_update=False,
                 avalability_check_delay = 10,
                 avalability_check_max_tries = 15,
                 elastic_host='elastic-meta-service.meta.svc',
                 elastic_port=9200,
                 elastic_index="meta-index",
                 check_in_pacs=True,
                 *args, 
                 **kwargs):

        self.dicom_operator = dicom_operator
        self.json_operator = json_operator
        self.jsonl_operator = jsonl_operator

        self.avalability_check_delay = avalability_check_delay
        self.avalability_check_max_tries = avalability_check_max_tries
        self.set_dag_id = set_dag_id
        self.no_update = no_update
        self.elastic_host = elastic_host
        self.elastic_port = elastic_port
        self.elastic_index = elastic_index
        self.instanceUID = None
        self.check_in_pacs = check_in_pacs

        super().__init__(
            dag=dag,
            name="json2meta",
            python_callable=self.start,
            *args, **kwargs
        )
