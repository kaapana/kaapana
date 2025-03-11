import glob
import json
import os
import requests
from kaapana.operators.HelperDcmWeb import get_dcmweb_helper
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator

from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings, OpensearchSettings
from kaapanapy.helper import get_opensearch_client

from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from opensearchpy.exceptions import NotFoundError

logger = get_logger(__name__)

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class LocalJson2MetaOperator(KaapanaPythonBaseOperator):
    """
    This operater pushes JSON data to OpenSearch.

    Pushes JSON data to the specified OpenSearch instance.
    If meta-data already exists, it can either be updated or replaced, depending on the replace parameter.
    If the operator fails, some or no data is pushed to OpenSearch.
    Further information about OpenSearch can be found here: https://opensearch.org/docs/latest/

    **Inputs:**

    * JSON data that should be pushed to OpenSearch

    **Outputs:**

    * If successful, the given JSON data is included in OpenSearch

    """

    def __init__(
        self,
        dag,
        dicom_operator=None,
        json_operator=None,
        jsonl_operator=None,
        set_dag_id: bool = False,
        replace: bool = False,
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
        :param replace: If there is a series found with the same ID, setting this to True will replace the series with new data. Otherwise, the document will be updated.
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
        self.replace = replace
        self.instanceUID = None
        self.check_in_pacs = check_in_pacs

        super().__init__(
            dag=dag,
            name="json2meta",
            python_callable=self.start,
            ram_mem_mb=10,
            **kwargs,
        )

    def push_to_opensearch(self, meta_information: dict):
        """
        Upload the meta-information in meta_information to following indices in OpenSearch:
        - project index: Derived from the field "00120020 ClinicalTrialProtocolID_keyword"
        - admin-project index: Derived from OpensearchSettings().default_index
        """
        logger.info(f"Pushing document to project index")
        try:
            clinical_trial_protocol_id = meta_information.get(
                "00120020 ClinicalTrialProtocolID_keyword"
            )
            project = self.get_project_by_name(clinical_trial_protocol_id)
            self.push_to_opensearch_index(
                new_document=meta_information,
                opensearch_index=project.get("opensearch_index"),
            )
        except:
            logger.warning(f"No project found for {clinical_trial_protocol_id}.")

        logger.info("Pushing document to admin-project index")
        self.push_to_opensearch_index(
            new_document=meta_information,
            opensearch_index=self.opensearch_index,
        )

    def push_to_opensearch_index(self, new_document: dict, opensearch_index: str):
        """
        Push a new document to a specific index.
        Compare the new document with the existing document in the index.
        """

        if "0020000E SeriesInstanceUID_keyword" in new_document:
            document_id = new_document["0020000E SeriesInstanceUID_keyword"]
        elif self.instanceUID is not None:
            document_id = self.instanceUID
        else:
            logger.error("No ID found! - exit")
            exit(1)
        new_document = self.sanitize_document(
            id=document_id,
            new_document=new_document,
            opensearch_index=opensearch_index,
        )
        response = self.os_client.index(
            index=opensearch_index,
            body=new_document,
            id=document_id,
            refresh=True,
        )

    def sanitize_document(self, id, new_document, opensearch_index):
        """
        Sanitize some fields in the document.
        If self.replace=False:
            Receive the old document from the index and update it with the new_document.

        Return the sanitized document.
        """

        # special treatment for bodypart regression since keywords don't match
        bpr_algorithm_name = "predicted_bodypart_string"
        bpr_key = "00000000 PredictedBodypart_keyword"
        if bpr_algorithm_name in new_document:
            new_document[bpr_key] = new_document[bpr_algorithm_name]
            del new_document[bpr_algorithm_name]

        if self.replace:
            return new_document

        logger.debug("Get old json from index.")
        try:
            old_document = self.os_client.get(index=opensearch_index, id=id)["_source"]
            logger.debug("Series already exists. Update the corresponding document.")
        except NotFoundError as e:
            logger.debug("Series not found in opensearch. Push new document.")
            return new_document

        old_document.update(new_document)
        return old_document

    def start(self, ds, **kwargs):
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
                            self.push_to_opensearch(obj)
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
                    self.push_to_opensearch(new_json)

    def get_project_by_name(self, project_name: str):
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
            params={"name": project_name},
        )
        response.raise_for_status()
        project = response.json()
        return project
