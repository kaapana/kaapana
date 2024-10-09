import glob
import json
import os
import pydicom
import time
import requests
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings, OpensearchSettings
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator


logger = get_logger(__name__)

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


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

    def push_to_project_index(self, json_dict):
        logger.info(f"Pushing JSON to project index : {json_dict}")
        id = json_dict["0020000E SeriesInstanceUID_keyword"]
        clinical_trial_protocol_id = json_dict.get(
            "00120020 ClinicalTrialProtocolID_keyword"
        )
        try:
            project = self.get_project_by_name(clinical_trial_protocol_id)
        except:
            logger.warning(f"No project found for {clinical_trial_protocol_id}")
            return None
        try:
            json_dict = self.produce_inserts(json_dict)
            response = self.os_client.index(
                index=project.get("opensearch_index"),
                body=json_dict,
                id=id,
                refresh=True,
            )
        except Exception as e:
            logger.error("Error while pushing JSON ...")
            raise (e)

    def push_json(self, json_dict):
        logger.info("Pushing JSON to admin-project index")
        if "0020000E SeriesInstanceUID_keyword" in json_dict:
            id = json_dict["0020000E SeriesInstanceUID_keyword"]
        elif self.instanceUID is not None:
            id = self.instanceUID
        else:
            logger.error("No ID found! - exit")
            exit(1)
        try:
            json_dict = self.produce_inserts(json_dict)
            response = self.os_client.index(
                index=self.opensearch_index,
                body=json_dict,
                id=id,
                refresh=True,
            )
        except Exception as e:
            logger.error("Error while pushing JSON ...")
            raise (e)

    def produce_inserts(self, new_json):
        logger.info("get old json from index.")
        try:
            old_json = self.os_client.get(
                index=self.opensearch_index, id=self.instanceUID
            )["_source"]
            print("Series already found in OS")
            if self.no_update:
                raise ValueError("ERROR")
        except Exception as e:
            logger.warning("doc is not updated! -> not found in os")
            logger.warning(str(e))
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
        from kaapanapy.helper import get_opensearch_client

        self.os_client = get_opensearch_client()
        self.dcmweb_helper = get_dcmweb_helper()
        self.opensearch_index = OpensearchSettings().default_index

        self.ti = kwargs["ti"]
        logger.info("Starting module json2meta")

        run_dir = os.path.join(self.airflow_workflow_dir, kwargs["dag_run"].run_id)
        batch_folder = [
            f for f in glob.glob(os.path.join(run_dir, self.batch_name, "*"))
        ]

        if self.dicom_operator is not None:
            self.rel_dicom_dir = self.dicom_operator.operator_out_dir
        else:
            self.rel_dicom_dir = self.operator_in_dir

        self.run_id = kwargs["dag_run"].run_id

        for batch_element_dir in batch_folder:
            if self.jsonl_operator:
                json_dir = os.path.join(
                    batch_element_dir, self.jsonl_operator.operator_out_dir
                )
                json_list = glob.glob(json_dir + "/**/*.jsonl", recursive=True)
                for json_file in json_list:
                    logger.info(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        for line in f:
                            obj = json.loads(line)
                            self.push_json(obj)
                            self.push_to_project_index(obj)
            else:
                json_dir = os.path.join(
                    batch_element_dir, self.json_operator.operator_out_dir
                )
                json_list = glob.glob(json_dir + "/**/*.json", recursive=True)
                logger.info(f"Found json files: {json_list}")
                assert len(json_list) > 0

                for json_file in json_list:
                    logger.info(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        new_json = json.load(f)
                    self.push_json(new_json)
                    self.push_to_project_index(new_json)

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

    def check_pacs_availability(self, instanceUID: str):
        print("#")
        print("# Checking if series available in PACS...")
        check_count = 0
        while not self.dcmweb_helper.check_if_series_in_archive(seriesUID=instanceUID):
            print("#")
            print(f"# Series {instanceUID} not found in PACS-> try: {check_count}")
            if check_count >= self.avalability_check_max_tries:
                print(
                    f"# check_count >= avalability_check_max_tries {self.avalability_check_max_tries}"
                )
                print("# Error! ")
                print("#")
                raise ValueError("ERROR")

            print(f"# -> waiting {self.avalability_check_delay} s")
            time.sleep(self.avalability_check_delay)
            check_count += 1

    def get_project_by_name(self, project_name: str):
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
            params={"name": project_name},
        )
        response.raise_for_status()
        project = response.json()
        return project

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

        self.avalability_check_delay = avalability_check_delay
        self.avalability_check_max_tries = avalability_check_max_tries
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
