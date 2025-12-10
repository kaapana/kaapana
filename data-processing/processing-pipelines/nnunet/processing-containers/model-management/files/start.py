import json
from glob import glob
from pathlib import Path
import zipfile
import os
from os.path import basename, exists, join, normpath
from shutil import rmtree
import re
from kaapanapy.logger import get_logger
from kaapanapy.helper import load_workflow_config
from kaapanapy.settings import ServicesSettings
import requests


logger = get_logger(__name__)


def extract_file_to_model_dir(zip_path, models_dir):
    """
    Extract the archive at zip_path to the models_dir.
    """
    Path(models_dir).mkdir(parents=True, exist_ok=True)
    logger.info(f"Unzipping {zip_path} -> {models_dir}")
    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(models_dir)
        return True, zip_path
    except Exception as e:
        logger.error("Could not extract model: {}".format(zip_path))
        logger.error("Target dir: {}".format(models_dir))
        logger.error("MSG: " + str(e))
        return False, zip_path

# Helper functions to read dataset.json and plans.json
# Functions moved from nnunet get_tasks()
def _get_dataset_json(model_path, installed_task):
    dataset_json_path = join(model_path, installed_task, "**", "dataset.json")
    print(f"1. DATASET_JSON_PATH: {dataset_json_path=}")
    dataset_json_path = glob(dataset_json_path, recursive=True)
    print(f"2. DATASET_JSON_PATH: {dataset_json_path=}")
    if len(dataset_json_path) > 0 and exists(dataset_json_path[-1]):
        dataset_json_path = dataset_json_path[-1]
        print(f"3. DATASET_JSON_PATH: {dataset_json_path=}")
        print(f"Found dataset.json at {dataset_json_path}")
        with open(dataset_json_path) as f:
            dataset_json = json.load(f)
    else:
        dataset_json = {}

    targets = []
    if "tracking_ids" in dataset_json:
        keys = list(dataset_json["tracking_ids"].keys())
        keys.sort(key=int)
        for key in keys:
            label = dataset_json["labels"][key]
            if key == "0" and label == "Clear Label":
                continue
            targets.append(label)
    elif "labels" in dataset_json:
        keys = list(dataset_json["labels"].keys())
        print(f"{keys=}")
        keys.remove("background")
        targets = keys
    else:
        targets.append("N/A")
    dataset_json["targets"] = targets

    input_modalty_list = []
    if "modality" in dataset_json:
        for key, input_modalty in dataset_json["modality"].items():
            input_modalty_list.append(input_modalty)
    else:
        input_modalty_list.append("N/A")
    dataset_json["input"] = input_modalty_list

    return dataset_json

def _get_plans_json(model_path, installed_task):
    plans_json_path = join(model_path, installed_task, "plans.json")
    with open(plans_json_path) as f:
        plans_json = json.load(f)
    return plans_json

def get_task_name_to_friendly_name_mapping():
    query_url = f"{ServicesSettings().kaapana_backend_url}/client/installed_models"
    try:
        res = requests.get(
            query_url,
            #headers=project_header,
        )
        if res.status_code != 200:
            raise Exception(f"ERROR: [{res.status_code}] {res.text}")
    except Exception as e:
        print(f"Processing of {identifiers=} threw an error.", e)
        raise e

def to_friendly_name(task_name: str) -> str:
    """Generate a friendly name in the format 'nnunet_<id>_<DATE_TIME>'."""
    dataset_pattern = r"Dataset(\d{3})"
    dataset_match = re.search(dataset_pattern, task_name)
    dataset_id = dataset_match.group(1) if dataset_match else None
    date_time_str = task_name.split("---")[0].split("_")[-1]
    default = f"nnunet_{dataset_id:03}_{date_time_str}"
    return default

def _get_installed_tasks(models_dir="/models/nnUNet"):

    installed_tasks = {}
    installed_models_path = models_dir
    if not exists(installed_models_path):
        return installed_tasks
    installed_models = [
        basename(normpath(f.path))
        for f in os.scandir(installed_models_path)
        if f.is_dir() and "ensembles" not in f.name
    ]
    for installed_model in installed_models:
        model_path = join(installed_models_path, installed_model)
        installed_tasks_dirs = [
            basename(normpath(f.path)) for f in os.scandir(model_path) if f.is_dir()
        ]
        for installed_task in installed_tasks_dirs:
            if installed_task not in installed_tasks:
                # get details installed tasks from dataset.json of installed tasks
                dataset_json = _get_dataset_json(
                    model_path=model_path, installed_task=installed_task
                )
                plans_json = _get_plans_json(
                    model_path=model_path, installed_task=installed_task
                )

                # and extract task's details to installed_tasks dict
                model_name = f"{installed_model}---{installed_task}"
                friendly_model_name = to_friendly_name(model_name)

                installed_tasks[friendly_model_name] = {
                    "description": dataset_json.get("description", "N/A"),
                    "input-mode": dataset_json.get("input-mode", "all"),
                    "input": list(dataset_json.get("channel_names", {}).values())
                    or "N/A",
                    "body_part": dataset_json.get("body_part", "N/A"),
                    "targets": dataset_json.get("targets", "N/A"),
                    "info": dataset_json.get("info", "N/A"),
                    "url": dataset_json.get("url", "N/A"),
                    "task_url": dataset_json.get("task_url", "N/A"),
                    "models_name": dataset_json.get("model", ["N/A"])[0],
                    "instance_name": dataset_json.get("instance_name", "N/A"),
                    "model_network_trainer": dataset_json.get("network_trainer", "N/A"),
                    "model_plan": plans_json.get("plans_name", "N/A"),
                    "task_ids": model_name
                }

    logger.info(f"INSTALLED TASKS: {installed_tasks}")
    return installed_tasks




def sync_models_in_database(models_dir="/models/nnUNet"):
    installed_tasks = _get_installed_tasks(models_dir=models_dir)
    query_url = f"{ServicesSettings().kaapana_backend_url}/client/installed_models/sync"
    workflow_config = load_workflow_config()
    project = workflow_config["project_form"]
    project_header = {"Project": json.dumps(project)}
    try:
        res = requests.put(
            query_url,
            json=dict(installed_models=installed_tasks),
            headers=project_header,
        )
        if res.status_code != 200:
            raise Exception(f"ERROR: [{res.status_code}] {res.text}")
    except Exception as e:
        print(f"Processing of threw an error.", e)
        raise e



def install_tasks():
    # Counter to check if smth has been processed
    processed_count = 0
    input_file_extension = "*.zip"
    workflow_dir = os.getenv("WORKFLOW_DIR", "None")
    workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
    assert workflow_dir is not None

    batch_name = os.getenv("BATCH_NAME", "None")
    batch_name = batch_name if batch_name.lower() != "none" else None
    assert batch_name is not None

    operator_in_dir = os.getenv("OPERATOR_IN_DIR", "None")
    operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
    assert operator_in_dir is not None

    operator_out_dir = os.getenv("OPERATOR_OUT_DIR", "None")
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None

    target_level = os.getenv("TARGET_LEVEL", "None")
    target_level = target_level if target_level.lower() != "none" else None
    assert target_level is not None

    logger.debug(f"target_level:     {target_level}")
    logger.debug(f"workflow_dir:     {workflow_dir}")
    logger.debug(f"batch_name:       {batch_name}")
    logger.debug(f"operator_in_dir:  {operator_in_dir}")
    logger.debug(f"operator_out_dir: {operator_out_dir}")

    # Loop for every batch-element (usually series)
    batch_folders = sorted(
        [f for f in glob(os.path.join("/", workflow_dir, batch_name, "*"))]
    )
    for batch_element_dir in batch_folders:

        logger.info(f"Processing batch-element {batch_element_dir}")
        element_input_dir = os.path.join(batch_element_dir, operator_in_dir)
        element_output_dir = os.path.join(batch_element_dir, operator_out_dir)

        # check if input dir present
        if not os.path.exists(element_input_dir):
            logger.warning.info(f"Input-dir: {element_input_dir} does not exists!")
            logger.warning.info("-> skipping")
            continue

        # creating output dir
        Path(element_output_dir).mkdir(parents=True, exist_ok=True)

        # creating output dir
        logger.debug("Search for model-zip-files...")
        if target_level == "default":
            models_dir = "/models/nnUNet"
        elif target_level == "batch":
            models_dir = os.path.join(workflow_dir, element_output_dir)
        elif target_level == "batch_element":
            models_dir = os.path.join(batch_element_dir, element_output_dir)
        else:
            logger.error(f"target_level: {target_level} not supported!")
            exit(1)

        input_files = glob(
            os.path.join(element_input_dir, input_file_extension), recursive=True
        )
        logger.info(f"Found {len(input_files)} input-files!")

        if len(input_files) == 0:
            logger.error("No zip-files could be found on batch-element-level")
            exit(1)
        elif len(input_files) != 1:
            logger.error("More than one zip-files were found -> unexpected -> abort.")
            exit(1)

        # Single process:
        # Loop for every input-file found with extension 'input_file_extension'
        for input_file in input_files:
            success, input_file = extract_file_to_model_dir(
                zip_path=input_file, models_dir=models_dir
            )
            if not success:
                exit(1)
            else:
                processed_count += 1

    if processed_count == 0:
        logger.error("----> NO FILES HAVE BEEN PROCESSED!")
        exit(1)
    
    logger.info(f"----> {processed_count} FILES HAVE BEEN PROCESSED!")
    logger.info("Successfully extracted model into model-dir.")


def uninstall_tasks(models_dir="/models/nnUNet"):
    """
    Remove the directory corresponding all tasks in 'uninstall_tasks' in the workflow_form of the workflow_config.
    The directory that will be removed is generated as <models_dir>/<dataset_directory>/<model_directory>
    If the <dataset_directory> is empty after the <model_directory> was removed it will also be removed.

    Example:
        uninstall_tasks = ['Dataset451_10.135.76.131_061124-144541---nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres']
        Path of removed directory:
        /models/nnUNet/Dataset451_10.135.76.131_061124-144541/nnUNetTrainer__nnUNetResEncUNetMPlans__3d_fullres
    """
    workflow_config = load_workflow_config()
    uninstall_task = workflow_config.get("workflow_form").get("task_ids")

    logger.info(f"tasks_to_uninstall:   {uninstall_task}")


    logger.info(f"Un-installing TASK: {uninstall_task}")

    dataset_directory_name, model_directory_name = tuple(
        uninstall_task.split("---")
    )
    dataset_path = Path(os.path.join(models_dir, dataset_directory_name))
    task_path = Path(
        os.path.join(models_dir, dataset_directory_name, model_directory_name)
    )

    assert task_path.is_dir()
    logger.info(f"Recursively remove {task_path=}")
    rmtree(task_path)

    try:
        dataset_path.rmdir()
        logger.info(f"Recursively remove {dataset_path=}")
    except OSError as e:
        if e.errno == 39:  ### Directory not empty error
            pass
        logger.error(f"Tried to remove the directory {dataset_path=}")
        raise e

    logger.info(f"{uninstall_task} successfully uninstalled!.")


if __name__ == "__main__":
    action = os.getenv("ACTION")

    if action == "install":
        install_tasks()
    elif action == "uninstall":
        uninstall_tasks()
    else:
        raise ValueError(
            f"{action=} not supported! Must be one of ['install','uninstall']"
        )
    sync_models_in_database()