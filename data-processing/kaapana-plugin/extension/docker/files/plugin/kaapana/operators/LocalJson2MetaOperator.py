import os
import json
import glob
import traceback
import logging
import pydicom
import errno
import time
from kaapana.operators.HelperDcmWeb import HelperDcmWeb
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.blueprints.kaapana_global_variables import BATCH_NAME, WORKFLOW_DIR
from opensearchpy import OpenSearch

class LocalJson2MetaOperator(KaapanaPythonBaseOperator):
    """
	This operater pushes JSON data to OpenSearch.

    Pushes JSON data to the specified OpenSearch instance. If meta-data already exists, it can either be updated or replaced, depending on the no_update parameter.
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
            id= json_dict["0020000E SeriesInstanceUID_keyword"]
        elif self.instanceUID is not None:
            id = self.instanceUID
        else:
            print("# No ID found! - exit")
            exit(1)
        try:
            response = self.os_client.index(
                index = self.opensearch_index,
                body = json_dict,
                id = id,
                refresh = True
            )
        except Exception as e:
            print("#")
            print("# Error while pushing JSON ...")
            print("#")
            exit(1)

        print("#")
        print("# Success")
        print("#")

    def start(self, ds, **kwargs):
        global es

        self.ti = kwargs['ti']
        print("# Starting module json2meta")

        run_dir = os.path.join(WORKFLOW_DIR, kwargs['dag_run'].run_id)
        batch_folder = [f for f in glob.glob(os.path.join(run_dir, BATCH_NAME, '*'))]

        if self.dicom_operator is not None:
            self.rel_dicom_dir = self.dicom_operator.operator_out_dir
        else:
            self.rel_dicom_dir = self.operator_in_dir

        self.run_id = kwargs['dag_run'].run_id
        print(("RUN_ID: %s" % self.run_id))

        for batch_element_dir in batch_folder:

            if self.jsonl_operator:
                json_dir = os.path.join(batch_element_dir, self.jsonl_operator.operator_out_dir)
                json_list = glob.glob(json_dir+'/**/*.jsonl', recursive=True)
                for json_file in json_list:
                    print(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding='utf-8') as f:
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
                print("#")
                print("#")
                print("#")
                print("####  Found json files: %s" % len(json_list))
                print("#")
                assert len(json_list) > 0

                for json_file in json_list:
                    print(f"Pushing file: {json_file} to META!")
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
                raise ValueError('ERROR')

            print(f"# -> waiting {self.avalability_check_delay} s")
            time.sleep(self.avalability_check_delay)
            check_count += 1


    def __init__(self,
                 dag,
                 dicom_operator=None,
                 json_operator=None,
                 jsonl_operator=None,
                 set_dag_id: bool = False,
                 no_update: bool = False,
                 avalability_check_delay: int = 10,
                 avalability_check_max_tries: int = 15,
                 opensearch_host: str = 'opensearch-service.meta.svc',
                 opensearch_port: int = 9200,
                 opensearch_index: str = "meta-index",
                 check_in_pacs: bool = True,
                 *args, 
                 **kwargs):

        """
		:param dicom_operator: Used to get OpenSearch document ID from dicom data. Only used with json_operator.
		:param json_operator: Provides json data, use either this one OR jsonl_operator.
		:param jsonl_operator: Provides json data, which is read and pushed line by line. This operator is prioritized over json_operator.
		:param set_dag_id: Only used with json_operator. Setting this to True will use the dag run_id as the OpenSearch document ID when dicom_operator is not given.
		:param no_update: If there is a series found with the same ID, setting this to True will replace the series with new data instead of updating it.
		:param avalability_check_delay: When checking for series availability in PACS, this parameter determines how many seconds are waited between checks in case series is not found.
		:param avalability_check_max_tries: When checking for series availability in PACS, this parameter determines how often to check for series in case it is not found.
		:param opensearch_host: Host address for OpenSearch.
		:param opensearch_port: Port for OpenSearch.
		:param opensearch_index: Specifies the index of OpenSearch where to put data into.
		:param check_in_pacs: Determines whether or not to search for series in PACS. If set to True and series is not found in PACS, the data will not be put into OpenSearch.
		"""



        self.dicom_operator = dicom_operator
        self.json_operator = json_operator
        self.jsonl_operator = jsonl_operator

        self.avalability_check_delay = avalability_check_delay
        self.avalability_check_max_tries = avalability_check_max_tries
        self.set_dag_id = set_dag_id
        self.no_update = no_update
        self.opensearch_host = opensearch_host
        self.opensearch_port = opensearch_port
        self.opensearch_index = opensearch_index
        self.instanceUID = None
        self.check_in_pacs = check_in_pacs
        auth = None
        # auth = ('admin', 'admin') # For testing only. Don't store credentials in code.
        self.os_client = OpenSearch(
            hosts = [{'host': self.opensearch_host, 'port': self.opensearch_port}],
            http_compress = True, # enables gzip compression for request bodies
            http_auth = auth,
            # client_cert = client_cert_path,
            # client_key = client_key_path,
            use_ssl = False,
            verify_certs = False,
            ssl_assert_hostname = False,
            ssl_show_warn = False,
            timeout=2,
            # ca_certs = ca_certs_path
        )

        super().__init__(
            dag=dag,
            name="json2meta",
            python_callable=self.start,
            **kwargs
        )
