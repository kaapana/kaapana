import json
import os
from glob import glob
from os.path import join, basename, dirname, normpath, exists

from kaapanapy.helper import get_project_user_access_token, get_opensearch_client
from kaapanapy.settings import OpensearchSettings

# instatiate opensearch access
access_token = get_project_user_access_token()
os_client = get_opensearch_client(access_token=access_token)
index = OpensearchSettings().default_index


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
                # and extract task's details to installed_tasks dict
                installed_tasks[f"{installed_model}---{installed_task}"] = {
                    "description": dataset_json["description"]
                    if "description" in dataset_json
                    else "N/A",
                    "model": [],
                    "input-mode": dataset_json["input-mode"]
                    if "input-mode" in dataset_json
                    else "all",
                    "input": list(dataset_json["channel_names"].values())
                    if "channel_names" in dataset_json
                    else "N/A",
                    "body_part": dataset_json["body_part"]
                    if "body_part" in dataset_json
                    else "N/A",
                    "targets": dataset_json["targets"]
                    if "targets" in dataset_json
                    else "N/A",
                    "supported": True,
                    "info": dataset_json["info"] if "info" in dataset_json else "N/A",
                    "url": dataset_json["url"] if "url" in dataset_json else "N/A",
                    "task_url": dataset_json["task_url"]
                    if "task_url" in dataset_json
                    else "N/A",
                }

    print(f"INSTALLED TASKS: {installed_tasks}")
    return installed_tasks


def get_tasks():
    try:
        af_home_path = "/kaapana/mounted/workflows"
        tasks, available_pretrained_task_names = _get_available_pretrained_tasks(
            af_home_path=af_home_path
        )
        installed_tasks = _get_installed_tasks(af_home_path=af_home_path)
        all_selectable_tasks = installed_tasks.copy()
        all_selectable_tasks.update(tasks)

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
    # compose query
    queryDict = {}
    queryDict["query"] = {
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
    }
    queryDict["_source"] = {}
    try:
        res = os_client.search(index=[index], body=queryDict)
        hits = res["hits"]["hits"]
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
