import json
import os
from glob import glob
from os.path import join, basename, dirname, normpath, exists


def get_dataset_json(model_path, installed_task):
    dataset_json_path = join(model_path, installed_task, "**", "dataset.json")
    dataset_json_path = glob(dataset_json_path, recursive=True)
    if len(dataset_json_path) > 0 and exists(dataset_json_path[-1]):
        dataset_json_path = dataset_json_path[-1]
        print(f"Found dataset.json at {dataset_json_path[-1]}")
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
        keys.sort(key=int)
        for key in keys:
            label = dataset_json["labels"][key]
            if key == "0" and label == "Clear Label":
                continue
            targets.append(label)
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

def get_available_pretrained_tasks(af_home_path):
    tasks_json_path = join(af_home_path, "dags", "nnunet", "nnunet_tasks.json")
    with open(tasks_json_path) as f:
        tasks = json.load(f)
    available_pretrained_task_names = [*{k: v for (k, v) in tasks.items() if "supported" in tasks[k] and tasks[k]["supported"]}]
    return tasks, available_pretrained_task_names

def get_installed_tasks(af_home_path):
    installed_tasks = {}
    installed_models_path = join("/models", "nnUNet")
    installed_models = [basename(normpath(f.path)) for f in os.scandir(installed_models_path) if f.is_dir() and "ensembles" not in f.name]
    for installed_model in installed_models:
        model_path = join(installed_models_path, installed_model)
        installed_tasks_dirs = [basename(normpath(f.path)) for f in os.scandir(model_path) if f.is_dir()]
        for installed_task in installed_tasks_dirs:
            if installed_task not in installed_tasks:
                dataset_json = get_dataset_json(model_path=model_path, installed_task=installed_task)
                installed_tasks[installed_task] = {
                    "description": dataset_json["description"] if "description" in dataset_json else "N/A",
                    "model": [],
                    "input-mode": dataset_json["input-mode"] if "input-mode" in dataset_json else "all",
                    "input": dataset_json["input"],
                    "body_part": dataset_json["body_part"] if "body_part" in dataset_json else "N/A",
                    "targets": dataset_json["targets"],
                    "supported": True,
                    "info": dataset_json["info"] if "info" in dataset_json else "N/A",
                    "url": dataset_json["url"] if "url" in dataset_json else "N/A",
                    "task_url": dataset_json["task_url"] if "task_url" in dataset_json else "N/A"
                }
            if installed_model not in installed_tasks[installed_task]["model"]:
                installed_tasks[installed_task]["model"].append(installed_model)
                installed_tasks[installed_task]["model"].sort()
    return installed_tasks

def get_tasks():
    af_home_path = "/root/airflow"
    tasks, available_pretrained_task_names = get_available_pretrained_tasks(af_home_path=af_home_path)
    installed_tasks = get_installed_tasks(af_home_path=af_home_path)
    all_selectable_tasks = installed_tasks.copy()
    all_selectable_tasks.update(tasks)

    return available_pretrained_task_names, installed_tasks, all_selectable_tasks
