import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from yaml import load_all, Loader
import glob
import os
import unittest
from .KaapanaAuth import KaapanaAuth
from .logger import get_logger
import logging
import time
import json

logger = get_logger(__name__, logging.INFO)


class CostumTestCase(unittest.TestCase):
    """
    This Testcase contains a single test method which dependes on the parameter given at initialization.
    """

    def __init__(
        self, testcase: dict, host: str, client_secret: str, timeout=3600
    ) -> None:
        """
        :param: testcase: contains the payload send to the kaapana backend to trigger an experiment.
        :param: host: ip address of the host, where the instance under test is deployed
        :param: client_secret: client secret of the kaapana client under test
        :timeout: time an experiment has before the test fails
        """
        self.form = testcase
        self.host = host
        self.client_secret = client_secret
        self.kaapana = WorkflowEndpoints(self.host, self.client_secret)
        self.timeout = timeout
        super().__init__(methodName="test_workflow")

    def test_workflow(self):
        """
        A generic test method derived from a dag_id and a JSON string.
        """
        form = self.form
        dag_id = form.get("dag_id")
        if form.get("ci_ignore", False) == True:
            logger.info(f"Ignore testcase for {dag_id=}")
            return None
        ### Check that dag is available
        if dag_id not in self.kaapana.get_dags():
            logger.warning(f"DAG {dag_id=} not available on the platform!")
            logger.warning(f"Skip test!")
            return None
        ### Adjust payload/form_data before triggering the workflow
        form["workflow_name"] = "ci_" + dag_id
        logger.info(f"Start testcase for {dag_id=}")
        instance_names = form.get("instance_names", [])
        if self.host not in instance_names:
            instance_names.append(self.host)
            form["instance_names"] = instance_names
        if (
            dag_id == "send-dicom"
            and form["conf_data"]["workflow_form"]["pacs_host"] == ""
        ):
            form["conf_data"]["workflow_form"]["pacs_host"] = self.host
        ### Trigger the workflow
        try:
            response = self.kaapana.submit_workflow(form)
        except Exception as e:
            logger.error(f"Failed triggering workflow {form=}")
            raise e
        workflow_name = response["workflow_name"]
        logger.info(f"Workflow {workflow_name} started for dag {dag_id}.")
        ### Wait for workflow to finish
        success, msg = self.wait_for_workflow(workflow_name)
        self.assertTrue(success, msg)
        logger.info(msg)

    def wait_for_workflow(self, workflow_name) -> tuple:
        """
        Check the status of all jobs in workflow <workflow_name> until all jobs finished, the run-time exceeds self.timeout or a single job failed.
        """
        start_time = time.time()
        jobs_info = []
        while abs(start_time - time.time()) < self.timeout:
            try:
                jobs_info = self.kaapana.get_jobs_info(workflow_name=workflow_name)
            except:
                pass
            jobs_status = [job.get("status") for job in jobs_info]
            logger.debug(f"jobs_info: {jobs_status}")
            if "failed" in jobs_status:
                msg = f"Workflow {workflow_name} failed: {jobs_info}"
                return False, msg
            elif jobs_status and jobs_status == ["finished" for _ in jobs_info]:
                msg = f"Workflow {workflow_name} succeeded."
                return True, msg
            else:
                time.sleep(5)
        msg = f"Workflow {workflow_name} exceeds timeout {self.timeout}"
        return False, msg


class WorkflowEndpoints(KaapanaAuth):
    def submit_workflow(self, payload):
        """
        Submit a workflow to the kaapana-backend API.
        """
        logger.debug(payload)
        r = self.request(
            "kaapana-backend/client/workflow",
            request_type=requests.post,
            json=payload,
            retries=1,
        )
        try:
            message = r.json()
        except json.decoder.JSONDecodeError as e:
            logger.error("Triggering the dag failed!")
            logger.error(r.text)
            raise e
        return message

    def get_dags(self) -> list:
        """
        Get a list of all DAGs installed on the platform
        """
        r = self.request(
            "kaapana-backend/client/dags?only_dag_names=true", request_type=requests.get
        )
        return r.json()

    def get_jobs_info(
        self, instance_name=None, workflow_name=None, status=None, limit=None
    ):
        """
        Get info about jobs from kaapana-backend API
        """
        params = {}
        if instance_name:
            params["instance_name"] = instance_name
        if workflow_name:
            params["workflow_name"] = workflow_name
        if status:
            params["status"] = status
        if limit:
            params["limit"] = limit
        r = self.request(
            "kaapana-backend/client/jobs", request_type=requests.get, params=params
        )
        return r.json()

    def trigger_multiple_testcases(self, testcases):
        """
        Trigger multiple dags from a list of testcases.
        """
        messages = []
        for form in testcases:
            message = self.submit_workflow(form)
            messages += message
        return messages


def read_payload_from_yaml(file_path):
    """
    Load dag run specific data from a yaml file.
    Translate this data into json strings.
    Output a list of tuples (dag_id, json-string)
    """
    testcases = []
    if os.stat(file_path).st_size == 0:
        return []

    with open(file_path) as f:
        for case in load_all(f, Loader=Loader):
            testcases.append(case)
    return testcases


def collect_all_testcases(testcase_dir):
    """
    Create a list of testcases, where each testcase is specified by the dag_id and a JSON string.
    Search through the testcase_dir and process all YAML files.
    """
    list_of_yaml_files = glob.glob(
        os.path.join(testcase_dir, "**/*.yaml"), recursive=True
    )
    logger.debug(f"yaml files: {list_of_yaml_files}")
    list_of_testcases = []

    for file in list_of_yaml_files:
        if testcases := read_payload_from_yaml(file):
            list_of_testcases += testcases
    return list_of_testcases
