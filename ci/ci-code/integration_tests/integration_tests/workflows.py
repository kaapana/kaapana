import json
import logging
import os
from pathlib import Path

import requests
from integration_tests.utils.KaapanaAuth import KaapanaAuth
from integration_tests.utils.logger import get_logger
from yaml import Loader, load_all

logger = get_logger(__name__, logging.INFO)


class WorkflowEndpoints(KaapanaAuth):
    def __init__(self, host, client_secret):
        super().__init__(host, client_secret)

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


def collect_testcase_files(testcase_dir):
    """
    Search through the testcase_dir and return all YAML files in a deterministic order.
    """
    list_of_yaml_files = sorted(Path(testcase_dir).rglob("*.yaml"))
    logger.debug(f"yaml files: {list_of_yaml_files}")
    return list_of_yaml_files
