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

class WorkflowEndpoints(KaapanaAuth):
    def submit_workflow(self, payload):
        """
        Submit a workflow to the kaapana-backend API.
        """
        logger.debug(payload)
        r = self.request(
            "kaapana-backend/client/workflow",
            request_type=requests.post,
            _json=payload,
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
            if case is not None:
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
