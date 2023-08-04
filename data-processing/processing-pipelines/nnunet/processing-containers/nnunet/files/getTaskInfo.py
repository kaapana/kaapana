import os
import glob
import json


def get_task_info(task):
    tasks_json_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), "prediction_tasks.json"
    )
    task_info = {}
    print("Getting task-info...")

    if os.path.isfile(tasks_json_path):
        with open(tasks_json_path) as f:
            tasks_dict = json.load(f)

            if task in tasks_dict:
                task_info = tasks_dict[task]
            else:
                print("task '{}' was not found in tasks.json! -> abort!".format(task))
                exit(1)
    else:
        print("tasks.json was not found at: {} -> abort!".format(tasks_json_path))
        exit(1)

    return task_info
