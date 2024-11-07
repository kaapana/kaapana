import json
import os
import re
from glob import glob
from os.path import basename, exists, join, normpath
from typing import Dict
from kaapana.operators.HelperOpensearch import HelperOpensearch


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


def _get_available_pretrained_tasks(af_home_path):
    tasks_json_path = join(af_home_path, "dags", "nnunet", "nnunet_tasks.json")
    with open(tasks_json_path) as f:
        tasks = json.load(f)
    available_pretrained_task_names = [
        *{
            k: v
            for (k, v) in tasks.items()
            if "supported" in tasks[k] and tasks[k]["supported"]
        }
    ]
    return tasks, available_pretrained_task_names


def _get_installed_tasks(af_home_path):
    installed_tasks = {}
    installed_models_path = join("/kaapana/mounted/workflows/models", "nnUNet")
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
                save_task_name(model_name)
                friendly_model_name = to_friendly_name(model_name)

                installed_tasks[friendly_model_name] = {
                    "description": dataset_json.get("description", "N/A"),
                    "input-mode": dataset_json.get("input-mode", "all"),
                    "input": list(dataset_json.get("channel_names", {}).values())
                    or "N/A",
                    "body_part": dataset_json.get("body_part", "N/A"),
                    "targets": dataset_json.get("targets", "N/A"),
                    "supported": True,
                    "info": dataset_json.get("info", "N/A"),
                    "url": dataset_json.get("url", "N/A"),
                    "task_url": dataset_json.get("task_url", "N/A"),
                    "model_name": dataset_json.get("model", ["N/A"])[0],
                    "instance_name": dataset_json.get("instance_name", "N/A"),
                    "model_network_trainer": dataset_json.get("network_trainer", "N/A"),
                    "model_plan": plans_json.get("plans_name", "N/A"),
                }

    print(f"INSTALLED TASKS: {installed_tasks}")
    return installed_tasks


def get_task_name_to_friendly_name_mapping() -> Dict[str, str]:
    models_path = "/kaapana/mounted/workflows/models/models.json"

    if os.path.isfile(models_path):
        with open(models_path, "r") as fp:
            try:
                mappings = json.load(fp)
                return mappings

            except json.JSONDecodeError:
                print("Error: JSON file is corrupted.")
    return {}


def to_friendly_name(task_name: str) -> str:
    """Generate a friendly name in the format 'nnunet_<id>_<DATE_TIME>'."""
    mapping = get_task_name_to_friendly_name_mapping()
    friendly_name = mapping.get(task_name)
    if friendly_name:
        return friendly_name

    dataset_pattern = r"Dataset(\d{3})"
    dataset_match = re.search(dataset_pattern, task_name)
    dataset_id = dataset_match.group(1) if dataset_match else None
    date_time_str = task_name.split("---")[0].split("_")[-1]
    default = f"nnunet_{dataset_id:03}_{date_time_str}"
    return default


def to_task_name(friendly_name: str) -> str:
    """Retrieve the task name associated with the given friendly name from models.json."""
    mapping = get_task_name_to_friendly_name_mapping()
    reverse_mapping = {v: k for k, v in mapping.items()}
    return reverse_mapping.get(friendly_name)


def delete_task_name(task_name: str) -> None:
    models_file = "/kaapana/mounted/workflows/models/models.json"

    # Initialize an empty dictionary for mappings
    mappings = {}

    # Check if the file exists and load existing mappings
    if os.path.isfile(models_file):
        with open(models_file, "r") as fp:
            try:
                mappings = json.load(fp)
            except json.JSONDecodeError:
                print("Warning: Existing JSON file is corrupted. Recreating the file.")

    mappings.pop(task_name, None)

    with open(models_file, "w") as fp:
        json.dump(mappings, fp, indent=4)


def save_task_name(task_name: str) -> None:
    """Save a mapping from task name to friendly name in models.json, creating a unique ID for each entry."""

    models_file = "/kaapana/mounted/workflows/models/models.json"

    # Initialize an empty dictionary for mappings
    mappings = {}

    # Check if the file exists and load existing mappings
    if os.path.isfile(models_file):
        with open(models_file, "r") as fp:
            try:
                mappings = json.load(fp)
            except json.JSONDecodeError:
                print("Warning: Existing JSON file is corrupted. Recreating the file.")

    # If task name was already saved
    if task_name in mappings.keys():
        return

    # If task name was not saved yet
    mappings[task_name] = to_friendly_name(task_name)
    with open(models_file, "w") as fp:
        json.dump(mappings, fp, indent=4)


def get_tasks():
    try:
        af_home_path = "/kaapana/mounted/workflows"
        tasks, available_pretrained_task_names = _get_available_pretrained_tasks(
            af_home_path=af_home_path
        )
        installed_tasks = _get_installed_tasks(af_home_path=af_home_path)
        all_selectable_tasks = installed_tasks.copy()
        all_selectable_tasks.update(tasks)

        # TODO why do we need to return all three?
        return available_pretrained_task_names, installed_tasks, all_selectable_tasks
    except Exception as e:
        print("Error in getTasks.py: ", e)
        return [], {}, {}


def get_all_checkpoints():
    try:
        nnunet_path = "/kaapana/mounted/workflows/models/nnUNet"
        checkpoints = glob(f"{nnunet_path}/**/**/**/**/*.model")
        checkpoints = [
            "/".join(i.replace(nnunet_path, "")[1:].split("/")[:-1])
            for i in checkpoints
        ]
        return checkpoints[::-1]

    except Exception as e:
        print("Error in get_all_model_checkpoints.py: ", e)
        return []


def get_available_protocol_names():
    try:
        hits = HelperOpensearch.get_query_dataset(
            query={
                "bool": {
                    "must": [
                        {"match_all": {}},
                        {
                            "match_phrase": {
                                "00080060 Modality_keyword.keyword": {"query": "OT"}
                            }
                        },
                    ],
                }
            },
            index="meta-index",
        )
        print(f"HITS: {hits=}")

        available_protocol_names = []
        if hits is not None:
            for hit in hits:
                if "00181030 ProtocolName_keyword" in hit["_source"]:
                    available_protocol_name_hits = hit["_source"][
                        "00181030 ProtocolName_keyword"
                    ]
                    if isinstance(available_protocol_name_hits, str):
                        available_protocol_name_hits = [available_protocol_name_hits]
                    available_protocol_names = (
                        available_protocol_names + available_protocol_name_hits
                    )
        print(f"AVAILABLE_PROTOCOL_NAMES: {available_protocol_names=}")
        return available_protocol_names

    except Exception as e:
        print("Error in get_available_protocol_names: ", e)
        return []
