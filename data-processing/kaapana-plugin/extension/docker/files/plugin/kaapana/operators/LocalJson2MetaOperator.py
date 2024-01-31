import os
import json
import glob
import traceback
import logging
import pydicom
import errno
import time

import requests

from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.HelperOpensearch import HelperOpensearch
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE


class LocalJson2MetaOperator(KaapanaPythonBaseOperator):
    """
    This operater pushes JSON data to OpenSearch.

    Pushes JSON data to the specified OpenSearch instance.
    If meta-data already exists, it can either be updated or replaced, depending on the no_update parameter.
    If the operator fails, some or no data is pushed to OpenSearch.
    Further information about OpenSearch can be found here: https://opensearch.org/docs/latest/

    **Inputs:**

    * JSON data that should be pushed to OpenSearch

    **Outputs:**

    * If successful, the given JSON data is included in OpenSearch

    """

    def push_json(self, json_dict):
        print("# Pushing JSON ...")
        if "0020000E SeriesInstanceUID_keyword" in json_dict:
            id = json_dict["0020000E SeriesInstanceUID_keyword"]
        elif self.instanceUID is not None:
            id = self.instanceUID
        else:
            print("# No ID found! - exit")
            exit(1)
        try:
            json_dict = self.produce_inserts(json_dict)
            response = HelperOpensearch.os_client.index(
                index=HelperOpensearch.index, body=json_dict, id=id, refresh=True
            )
        except Exception as e:
            print("#")
            print("# Error while pushing JSON ...")
            print("#")
            print(e)
            exit(1)

        print("#")
        print("# Success")
        print("#")

    def produce_inserts(self, new_json):
        print("INFO: get old json from index.")
        try:
            old_json = HelperOpensearch.os_client.get(
                index=HelperOpensearch.index, id=self.instanceUID
            )["_source"]
            print("Series already found in OS")
            if self.no_update:
                raise ValueError("ERROR")
        except Exception as e:
            print("doc is not updated! -> not found in os")
            print(e)
            old_json = {}

        # special treatment for bodypart regression since keywords don't match
        bpr_algorithm_name = "predicted_bodypart_string"
        bpr_key = "00000000 PredictedBodypart_keyword"
        if bpr_algorithm_name in new_json:
            new_json[bpr_key] = new_json[bpr_algorithm_name]
            del new_json[bpr_algorithm_name]

        for new_key in new_json:
            new_value = new_json[new_key]
            old_json[new_key] = new_value

        return old_json

    def start(self, ds, **kwargs):
        global es

        self.ti = kwargs["ti"]
        print("# Starting module json2meta")

        run_dir = os.path.join(self.airflow_workflow_dir,
                               kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        if self.dicom_operator is not None:
            self.rel_dicom_dir = self.dicom_operator.operator_out_dir
        else:
            self.rel_dicom_dir = self.operator_in_dir

        self.run_id = kwargs["dag_run"].run_id
        print(("RUN_ID: %s" % self.run_id))

        for batch_element_dir in batch_folder:
            if self.jsonl_operator:
                json_dir = os.path.join(
                    batch_element_dir, self.jsonl_operator.operator_out_dir
                )
                json_list = glob.glob(json_dir + "/**/*.jsonl", recursive=True)
                if len(json_list) == 0:
                    print("+++++++++++++++++++++++++++++++")
                    print("++++++++ NO JSON FOUND! +++++++")
                    print("+++++++++++++++++++++++++++++++")
                for json_file in json_list:
                    print(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        for line in f:
                            obj = json.loads(line)
                            self.push_json(obj)
            else:
                # TODO: is this dcm check necessary? InstanceID is set in upload
                # dcm_files = sorted(
                #     glob.glob(
                #         os.path.join(batch_element_dir, self.rel_dicom_dir, "*.dcm*"),
                #         recursive=True,
                #     )
                # )
                # self.set_id(dcm_files[0])

                json_dir = os.path.join(
                    batch_element_dir, self.json_operator.operator_out_dir
                )
                print(("Pushing json files from: %s" % json_dir))
                json_list = glob.glob(json_dir + "/**/*.json", recursive=True)
                print("#")
                print("#")
                print("#")
                print("####  Found json files: %s" % len(json_list))
                print("#")
                assert len(json_list) > 0

                for json_file in json_list:
                    print(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        new_json = json.load(f)
                    self.push_json(new_json)

    def set_id(self, dcm_file=None):
        if dcm_file is not None:
            self.instanceUID = pydicom.dcmread(dcm_file)[0x0020, 0x000E].value
            self.patient_id = pydicom.dcmread(dcm_file)[0x0010, 0x0020].value
            print(("Dicom instanceUID: %s" % self.instanceUID))
            print(("Dicom Patient ID: %s" % self.patient_id))
        elif self.set_dag_id:
            self.instanceUID = self.run_id
        else:
            print("dicom_operator and dct_to_push not specified!")

    def __init__(
        self,
        dag,
        dicom_operator=None,
        json_operator=None,
        jsonl_operator=None,
        set_dag_id: bool = False,
        no_update: bool = False,
        avalability_check_delay: int = 10,
        avalability_check_max_tries: int = 15,
        check_in_pacs: bool = True,
        **kwargs,
    ):
        """
        :param dicom_operator: Used to get OpenSearch document ID from dicom data. Only used with json_operator.
        :param json_operator: Provides json data, use either this one OR jsonl_operator.
        :param jsonl_operator: Provides json data, which is read and pushed line by line. This operator is prioritized over json_operator.
        :param set_dag_id: Only used with json_operator. Setting this to True will use the dag run_id as the OpenSearch document ID when dicom_operator is not given.
        :param no_update: If there is a series found with the same ID, setting this to True will replace the series with new data instead of updating it.
        :param avalability_check_delay: When checking for series availability in PACS, this parameter determines how many seconds are waited between checks in case series is not found.
        :param avalability_check_max_tries: When checking for series availability in PACS, this parameter determines how often to check for series in case it is not found.
        :param check_in_pacs: Determines whether or not to search for series in PACS. If set to True and series is not found in PACS, the data will not be put into OpenSearch.
        """

        self.dicom_operator = dicom_operator
        self.json_operator = json_operator
        self.jsonl_operator = jsonl_operator
        self.set_dag_id = set_dag_id
        self.no_update = no_update
        self.instanceUID = None
        self.check_in_pacs = check_in_pacs

        super().__init__(
            dag=dag,
            name="json2meta",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )
