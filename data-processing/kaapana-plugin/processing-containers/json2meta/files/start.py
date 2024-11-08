import glob
import json
import os
from os import getenv
from os.path import exists, join

import pydicom
import requests
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.logger import get_logger
from kaapanapy.settings import KaapanaSettings
from kaapanapy.settings import OpensearchSettings

logger = get_logger(__name__, level="INFO")

SERVICES_NAMESPACE = KaapanaSettings().services_namespace


class Json2MetaOperator:
    """
    This operater pushes JSON data to OpenSearch.

    Pushes JSON data to the specified OpenSearch instance.
    If meta-data already exists, it can either be updated or replaced, depending on the no_update parameter.
    If the operator fails, some or no data is pushed to OpenSearch.
    Further information about OpenSearch can be found here: https://opensearch.org/docs/latest/

    **Inputs:**

    * JSON data that should be pushed to OpenSearch
    * DICOM data that is used to get the OpenSearch document ID

    **Outputs:**

    * If successful, the given JSON data is included in OpenSearch

    """

    def __init__(
        self,
        dicom_operator_out_dir: str = None,
        json_operator_out_dir: str = None,
        jsonl_operator_out_dir: str = None,
        set_dag_id: bool = False,
        no_update: bool = False,
        avalability_check_delay: int = 10,
        avalability_check_max_tries: int = 15,
        operator_in_dir: str = None,
        workflow_dir: str = None,
        batch_name: str = None,
        run_id: str = None,
    ):
        """Initializes the Json2MetaOperator

        Args:
            dicom_operator_out_dir (str, optional): Output directory of the dicom operator. Defaults to None.
            json_operator_out_dir (str, optional): Output directory of the json operator. Defaults to None.
            jsonl_operator_out_dir (str, optional): Output directory of the jsonl operator. Defaults to None.
            set_dag_id (bool, optional): Bool to set the dag id. Defaults to False.
            no_update (bool, optional): Bool to update the json. Defaults to False.
            avalability_check_delay (int, optional): Seconds to wait between checks. Defaults to 10.
            avalability_check_max_tries (int, optional): Max tries to check. Defaults to 15.
            operator_in_dir (str, optional): _description_. Defaults to None.
            workflow_dir (str, optional): _description_. Defaults to None.
            batch_name (str, optional): _description_. Defaults to None.
            run_id (str, optional): _description_. Defaults to None.
        """

        self.dicom_operator_out_dir = dicom_operator_out_dir
        self.json_operator_out_dir = json_operator_out_dir
        self.jsonl_operator_out_dir = jsonl_operator_out_dir
        self.operator_in_dir = operator_in_dir
        self.workflow_dir = workflow_dir
        self.batch_name = batch_name
        self.run_id = run_id

        self.avalability_check_delay = avalability_check_delay
        self.avalability_check_max_tries = avalability_check_max_tries
        self.set_dag_id = set_dag_id
        self.no_update = no_update

        self.series_instance_uid = None
        self.study_instance_uid = None
        self.patient_id = None
        self.clinical_trial_protocol_id = None

        config_path = os.path.join(self.workflow_dir, "conf", "conf.json")
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                self.workflow_config = json.load(f)

        self.project_id = self.workflow_config.get("project_form", {}).get("id", None)
        self.opensearch_settings = OpensearchSettings()

    def push_to_project_index(self, json_dict: dict):
        """Pushes JSON data to the project index

        Args:
            json_dict (dict): JSON data to push
        """
        logger.info(f"Pushing JSON to project index")

        if self.project_id:
            project_id = self.project_id
            logger.info(f"Project ID taken from workflow config: {project_id}")
        else:
            project = self.get_project_by_name(self.clinical_trial_protocol_id)
            project_id = project.get("id")
            logger.info(f"Project ID taken from ClinicalTrialProtocolID: {project_id}")

        json_dict = self.produce_inserts(json_dict, project.get("opensearch_index"))
        try:
            _ = HelperOpensearch.os_client.index(
                index=project.get("opensearch_index"),
                body=json_dict,
                id=self.series_instance_uid,
                refresh=True,
            )
        except Exception as e:
            logger.error("Error while pushing JSON ...")
            raise (e)

    def push_json(self, json_dict: dict):
        """Pushes JSON data to admin project index in OpenSearch

        Args:
            json_dict (dict): JSON data to push
        """
        logger.info("Pushing JSON admin project index")
        if "0020000E SeriesInstanceUID_keyword" in json_dict:
            id = json_dict["0020000E SeriesInstanceUID_keyword"]
        elif self.series_instance_uid is not None:
            id = self.series_instance_uid
        else:
            logger.error("No ID found! - exit")
            exit(1)

        json_dict = self.produce_inserts(
            json_dict, self.opensearch_settings.default_index
        )
        try:
            _ = HelperOpensearch.os_client.index(
                index=self.opensearch_settings.default_index,
                body=json_dict,
                id=id,
                refresh=True,
            )
        except Exception as e:
            logger.error("Error while pushing JSON ...")
            raise (e)

    def produce_inserts(self, new_json: dict, index: str = None):
        """Produces inserts for OpenSearch

        Args:
            new_json (dict): JSON data to insert
            index (str, optional): Index to insert to. Defaults to None.

        Raises:
            ValueError: If the series is not found

        Returns:
            dict: Updated JSON data which will be pushed to OpenSearch
        """
        logger.info("get old json from index.")

        # Try to get the series from OpenSearch
        old_json = HelperOpensearch.get_series_metadata(
            series_instance_uid=self.series_instance_uid,
            index=index,
        )

        if old_json is None:
            logger.info(f"Series not found in OS. Creating new entry.")
            old_json = {}
        elif old_json and self.no_update:
            logger.error("Series already found in OS and no_update is set!")
            raise ValueError("Series already found in OS and no_update is set!")
        else:
            logger.warning("Series already found in OS, updating!")
            old_json = old_json

        # special treatment for bodypart regression since keywords don't match
        bpr_algorithm_name = "predicted_bodypart_string"
        bpr_key = "00000000 PredictedBodypart_keyword"
        if bpr_algorithm_name in new_json:
            logger.info("Special treatment for BPR")
            new_json[bpr_key] = new_json[bpr_algorithm_name]
            new_json.pop(bpr_algorithm_name)

        old_json.update(new_json)

        return old_json

    def set_dicom_globals(self, path: str):
        """Sets the study and series instance UID

        Args:
            path (str): Path to the dicom file
        """

        ds = pydicom.dcmread(path)
        self.series_instance_uid = ds[0x0020, 0x000E].value
        self.study_instance_uid = ds[0x0020, 0x000D].value
        self.patient_id = ds[0x0010, 0x0020].value
        self.clinical_trial_protocol_id = ds[0x0012, 0x0020].value

    def start(self):
        """Starts the Json2MetaOperator"""

        logger.info("Starting module json2meta")

        batch_folder = glob.glob(join("/", self.workflow_dir, self.batch_name, "*"))

        if self.dicom_operator_out_dir:
            self.rel_dicom_dir = self.dicom_operator_out_dir
        else:
            self.rel_dicom_dir = self.operator_in_dir

        for batch_element_dir in batch_folder:

            # Set the dicom globals
            path_to_dicom = join(batch_element_dir, self.rel_dicom_dir)
            dicom_list = glob.glob(path_to_dicom + "/**/*.dcm", recursive=True)
            self.set_dicom_globals(dicom_list[0])

            if self.jsonl_operator_out_dir:
                json_dir = os.path.join(batch_element_dir, self.jsonl_operator_out_dir)
                json_list = glob.glob(json_dir + "/**/*.jsonl", recursive=True)
                for json_file in json_list:
                    logger.info(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        for line in f:
                            obj = json.loads(line)
                            self.push_json(obj)
                            self.push_to_project_index(obj)
            else:
                json_dir = os.path.join(batch_element_dir, self.json_operator_out_dir)
                json_list = glob.glob(json_dir + "/**/*.json", recursive=True)
                logger.info(f"Found json files: {json_list}")
                assert len(json_list) > 0

                for json_file in json_list:
                    logger.info(f"Pushing file: {json_file} to META!")
                    with open(json_file, encoding="utf-8") as f:
                        new_json = json.load(f)
                    self.push_json(new_json)
                    self.push_to_project_index(new_json)

    def get_project_by_name(self, project_name: str) -> dict:
        """Gets a project by name

        Args:
            project_name (str): Name of the project

        Returns:
            dict: Project data
        """
        response = requests.get(
            f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}",
        )
        response.raise_for_status()
        project = response.json()
        return project


if __name__ == "__main__":

    dicom_operator_out_dir = getenv("DICOM_OPERATOR_OUT_DIR", None)
    json_operator_out_dir = getenv("JSON_OPERATOR_OUT_DIR", None)
    jsonl_operator_out_dir = getenv("JSONL_OPERATOR_OUT_DIR", None)
    avalability_check_delay = int(getenv("AVALABILITY_CHECK_DELAY", 10))
    avalability_check_max_tries = int(getenv("AVALABILITY_CHECK_MAX_TRIES", 15))

    set_dag_id = getenv("SET_DAG_ID", False)
    set_dag_id = set_dag_id.lower() == "true"

    no_update = getenv("NO_UPDATE", False)
    no_update = no_update.lower() == "true"

    operator_in_dir = getenv("OPERATOR_IN_DIR", None)
    assert (
        operator_in_dir is not None or dicom_operator_out_dir is not None
    ), "No input directory specified for dicom files!, please set OPERATOR_IN_DIR or DICOM_OPERATOR_OUT_DIR"

    workflow_dir = getenv("WORKFLOW_DIR", None)
    if not exists(workflow_dir):
        # Workaround if this is being run in dev-server
        workflow_dir_dev = workflow_dir.split("/")
        workflow_dir_dev.insert(3, "workflows")
        workflow_dir_dev = "/".join(workflow_dir_dev)

        if not exists(workflow_dir_dev):
            raise Exception(f"Workflow directory {workflow_dir} does not exist!")

        workflow_dir = workflow_dir_dev

    batch_name = getenv("BATCH_NAME", None)
    assert batch_name, "Batch name is not set!"

    run_id = getenv("RUN_ID", None)
    assert run_id, "Run ID is not set!"

    operator = Json2MetaOperator(
        dicom_operator_out_dir=dicom_operator_out_dir,
        json_operator_out_dir=json_operator_out_dir,
        jsonl_operator_out_dir=jsonl_operator_out_dir,
        avalability_check_delay=avalability_check_delay,
        avalability_check_max_tries=avalability_check_max_tries,
        set_dag_id=set_dag_id,
        no_update=no_update,
        operator_in_dir=operator_in_dir,
        workflow_dir=workflow_dir,
        batch_name=batch_name,
        run_id=run_id,
    )

    operator.start()
