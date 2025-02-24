import json
import os
import shutil
import time
from glob import glob
from os.path import exists, join
from re import sub

import pydicom
import requests
from airflow.api.common.trigger_dag import trigger_dag as trigger
from airflow.models import DagBag
from kaapana.blueprints.kaapana_global_variables import SERVICES_NAMESPACE
from kaapana.blueprints.kaapana_utils import generate_run_id
from kaapana.operators.KaapanaPythonBaseOperator import KaapanaPythonBaseOperator
from kaapana.operators.LocalGetInputDataOperator import LocalGetInputDataOperator


# Define a function to convert a string to camel case
def camel_case(s: str):
    # Use regular expression substitution to replace underscores and hyphens with spaces,
    # then title case the string (capitalize the first letter of each word), and remove spaces
    s = sub(r"(_|-)+", " ", s).title().replace(" ", "")

    # Join the string, ensuring the first letter is lowercase
    return "".join([s[0].lower(), s[1:]])


# ignore the service prefix while retriving dag settings
# from the backend
def ignore_service_prefix(dagname: str):
    return dagname.replace("service-", "")


def _get_project_by_name(project_name):
    response = requests.get(
        f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080/projects/{project_name}"
    )
    response.raise_for_status()
    return response.json()


class LocalAutoTriggerOperator(KaapanaPythonBaseOperator):
    """
    Operator to trigger workflows from within a workflow.
    To automatically trigger workflows configuration JSON files with the name */*trigger_rule.json* are needed.
    The operator search for all files with this extension in the dags folder.

    **Inputs:**

    JSON file example:

    .. code-block:: python

        [{
            "search_tags": {
                "0x0008,0x0060": "SEG,RTSTRUCT" # comma separated values represent 'or'-logic
            },
            "dag_ids": {
                    <dag id to trigger>: {
                    "fetch_method": "copy",
                    "single_execution" : false,
                    "depends_on": "service-extract-metadata", # another dag from autotrigger, if current dag depends on the execution of another dag,
                    "get_settings_from_api": true, # make a request to settings backend to get dag settings using the dag name
                    "delay": 10 # integer in seconds, if one dag requires a depends on dag to finished executions.
                    }
            }
        }]

    **Outputs:**

    * all workflows with predefined trigger rules are triggered
    """

    def trigger_it(self, triggering):
        dag_id = triggering["dag_id"]
        dag_run_id = triggering["dag_run_id"]
        conf = triggering["conf"]
        print("#")
        print(f"# Triggering dag-id: {dag_id}")
        print(f"# Dag run id: '{dag_run_id}'")
        print(f"# conf: {conf}")
        print("#")
        trigger(dag_id=dag_id, run_id=dag_run_id, conf=conf, replace_microseconds=False)
        print(f"# Triggered! ")

    def set_data_input(self, dag_id, dcm_path, dag_run_id, series_uid, conf={}):
        print("Set input data")
        print(f"# conf: {conf}")
        print("#")
        if "fetch_method" in conf and conf["fetch_method"].lower() == "copy":
            print("# Searching DAG-id in DagBag:")
            for dag in DagBag().dags.values():
                if dag.dag_id == dag_id:
                    print(f"# found dag_id: {dag.dag_id}")
                    for task in dag.tasks:
                        if (
                            LocalGetInputDataOperator.__name__
                            == task.__class__.__name__
                        ):
                            print(
                                f"# found {LocalGetInputDataOperator.__name__} task: {task.name}"
                            )
                            get_input_dir_name = task.operator_out_dir
                            target = os.path.join(
                                self.airflow_workflow_dir,
                                dag_run_id,
                                "batch",
                                series_uid,
                                get_input_dir_name,
                            )
                            print(f"# Copy data to: {target}")
                            shutil.copytree(src=dcm_path, dst=target)
                            print("#")
                            break
                    break
        else:
            print(f"# Using PACS fetch-method !")

            if "data_form" not in conf or "identifiers" not in conf["data_form"]:
                conf["data_form"] = {"identifiers": []}
            conf["data_form"]["identifiers"].append(series_uid)

        return conf

    def order_trigger_items(self, triggering_list: list):
        """
        Reorders a list of triggering DAGs based on their dependencies and returns the reordered list.

        This function takes a list of trigger items, each containing configuration details. If an item
        has a "depends_on" field in its configuration, it is placed after the item it depends on in the
        reordered list. Items without dependencies are added directly to the reordered list. If an item
        depends on something that hasn't been added yet, it is temporarily cached and added at the end.
        A message is printed indicating how many items have been deferred to the end due to unmet
        dependencies.

        Args:
            triggering_list (list): A list of dictionaries where each dictionary represents a triggering
                                    item with at least "dag_id" and "conf" fields. The "conf" field can
                                    include a "depends_on" key indicating dependency on another DAG.

        Returns:
            list: A reordered list of triggering items with dependencies considered.

        Raises:
            AssertionError: If the length of the reordered list doesn't match the input list, indicating
                            a possible logic error.
        """
        reordered_list = []
        already_added_dag = []
        cached = []
        for triggering in triggering_list:
            if "depends_on" not in triggering["conf"]:
                reordered_list.append(triggering)
                already_added_dag.append(triggering["dag_id"])
                continue

            conf = triggering["conf"]
            if conf["depends_on"] in already_added_dag:
                reordered_list.append(triggering)
                already_added_dag.append(triggering["dag_id"])
            else:
                cached.append(triggering)
            del conf["depends_on"]

        if len(cached) > 0:
            print(f"{len(cached)} items have been shifted to the last.")

        reordered_list = reordered_list + cached
        assert len(reordered_list) == len(triggering_list)

        return reordered_list

    def get_workflow_settings_from_api(self, workflow_name: str):
        """
        Retrieves workflow settings from the backend API for a given workflow name.

        Converts the workflow name to camel case, constructs the API URL, and sends a GET request
        to fetch settings. If the request succeeds, returns the 'properties' field from the response.
        If the request fails or 'properties' is not present, returns an empty dictionary.

        Args:
            workflow_name (str): The name of the workflow whose settings are to be retrieved.

        Returns:
            dict: The properties of the workflow settings if available, otherwise an empty dictionary.

        Raises:
            Exception: If the API request fails with a non-200 status code.
        """
        client_endpoint = (
            f"http://kaapana-backend-service.{SERVICES_NAMESPACE}.svc:5000"
        )
        # convert the workflow name / DAG name to camel_case, since dag names are stored in
        # camel case in the backend
        workflow_settings_url = (
            f"{client_endpoint}/settings/workflows/{camel_case(workflow_name)}"
        )
        try:
            res = requests.get(
                workflow_settings_url,
                headers={"X-Forwarded-Preferred-Username": "system"},
            )
            if res.status_code != 200:
                raise Exception(f"ERROR: [{res.status_code}] {res.text}")
        except Exception as e:
            print(f"Request to get settings {workflow_name} threw an error.", e)

        result = res.json()
        if "properties" in result["value"]:
            return result["value"]["properties"]
        else:
            return {}

    def start(self, ds, **kwargs):
        print("# ")
        print("# Starting LocalAutoTriggerOperator...")
        print("# ")
        print(kwargs)
        trigger_rule_list = []
        for filePath in glob("/kaapana/mounted/workflows/**/*trigger_rule.json"):
            with open(filePath, "r") as f:
                print(f"Found auto-trigger configuration: {filePath}")
                trigger_rule_list = trigger_rule_list + json.load(f)

        print("# ")
        print(
            f"# Found {len(trigger_rule_list)} auto-trigger configurations -> start processing ..."
        )
        print("# ")

        batch_folders = sorted(
            [
                f
                for f in glob(
                    join(
                        self.airflow_workflow_dir,
                        kwargs["dag_run"].run_id,
                        "batch",
                        "*",
                    )
                )
            ]
        )
        triggering_list = []
        for batch_element_dir in batch_folders:
            print("#")
            print(f"# Processing batch-element {batch_element_dir}")
            print("#")

            element_input_dir = join(batch_element_dir, self.operator_in_dir)

            # check if input dir present
            if not exists(element_input_dir):
                print("#")
                print(f"# Input-dir: {element_input_dir} does not exists!")
                print("# -> skipping")
                print("#")
                continue

            input_files = glob(join(element_input_dir, "*.dcm"), recursive=False)
            print(f"# Found {len(input_files)} input-files!")

            incoming_dcm = pydicom.dcmread(input_files[0])
            dcm_dataset = (
                str(incoming_dcm[0x0012, 0x0020].value).lower()
                if (0x0012, 0x0020) in incoming_dcm
                else "N/A"
            )
            series_uid = str(incoming_dcm[0x0020, 0x000E].value)

            print("#")
            print(f"# dcm_dataset:     {dcm_dataset}")
            print(f"# series_uid:      {series_uid}")
            print("#")

            for idx, config_entry in enumerate(trigger_rule_list):
                print(f"# Checking trigger-rule: {idx}")
                fullfills_all_search_tags = True
                for search_key, search_value in config_entry["search_tags"].items():
                    print(f"# search_tag: {search_key}")
                    dicom_tag = search_key.split(",")
                    if dicom_tag not in incoming_dcm:
                        print(
                            f"# dicom_tag: {dicom_tag} could not be found in incoming dcm file -> skipping"
                        )
                        continue
                    incoming_tag_value = (
                        str(incoming_dcm[dicom_tag].value).lower()
                        if (dicom_tag in incoming_dcm)
                        else ""
                    )
                    search_tag_values = search_value.lower().split(",")
                    print(f"# incoming_tag_value: {incoming_tag_value}")
                    print(f"# search_tag_values:  {search_tag_values}")
                    if incoming_tag_value not in search_tag_values:
                        print(f"# No match identified for tag {dicom_tag}")
                        fullfills_all_search_tags = False
                    else:
                        print(f"# Match for tag {dicom_tag}! -> triggering")
                    print(f"#")

                if fullfills_all_search_tags:
                    for (
                        dag_id,
                        conf,
                    ) in config_entry["dag_ids"].items():
                        if dag_id == "service-extract-metadata" or (
                            dcm_dataset != "dicom-test"
                            and dcm_dataset != "phantom-example"
                        ):
                            print(f"# Triggering '{dag_id}'")
                            single_execution = False
                            if "single_execution" in conf and conf["single_execution"]:
                                # if it is a batch, still process triggered dag witout batch-processing
                                print("Single execution enabled for dag!")
                                single_execution = True
                            if single_execution:
                                dag_run_id = generate_run_id(dag_id)
                            else:
                                dag_run_id = ""
                                for triggering in triggering_list:
                                    if dag_id == triggering["dag_id"]:
                                        dag_run_id = triggering["dag_run_id"]
                                        conf = triggering["conf"]
                                        break
                                if not dag_run_id:
                                    dag_run_id = generate_run_id(dag_id)
                            conf = self.set_data_input(
                                dag_id=dag_id,
                                dcm_path=element_input_dir,
                                dag_run_id=dag_run_id,
                                series_uid=series_uid,
                                conf=conf,
                            )
                            conf["project_form"] = _get_project_by_name(
                                dcm_dataset.removeprefix("kp-")
                            )
                            if not single_execution:
                                for i in range(len(triggering_list)):
                                    if triggering_list[i]["dag_id"] == dag_id:
                                        del triggering_list[i]
                                        break

                            triggering_list.append(
                                {
                                    "dag_id": dag_id,
                                    "conf": conf,
                                    "dag_run_id": dag_run_id,
                                }
                            )

        # try reordering the DAGS if any DAG has `depends_on` properties
        # set on its trigger rule and depends another DAG to be executed
        # first.
        triggering_list = self.order_trigger_items(triggering_list)
        for triggering in triggering_list:
            conf = triggering["conf"]
            # 'delay' autotrigger rule,
            # integer in seconds, if one dag requires an earlier excuted autotriggered dag
            # to finished executions.
            if "delay" in conf:
                print(f"Delaying {triggering['dag_id']} by {conf['delay']} seconds.")
                time.sleep(conf["delay"])
                # delete `delay` from the config
                del conf["delay"]
            if "get_settings_from_api" in conf and conf["get_settings_from_api"]:
                # make a request to settings backend to get dag settings using the dag name
                # remove the service prefix from the service dag name
                workflow_form_data = self.get_workflow_settings_from_api(
                    ignore_service_prefix(triggering["dag_id"])
                )
                if "service" not in triggering["dag_id"]:
                    workflow_form_data["username"] = "system"
                conf["form_data"] = workflow_form_data
                # delete `get_settings_from_api` from the config
                del conf["get_settings_from_api"]

            self.trigger_it(triggering)

    def __init__(self, dag, **kwargs):
        super().__init__(
            dag=dag, name="auto-dag-trigger", python_callable=self.start, **kwargs
        )
