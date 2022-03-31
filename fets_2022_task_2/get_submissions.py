import json
import os
import shlex
import shutil
import subprocess
from datetime import datetime
import traceback
import time
import sys

# import docker
import numpy as np
import synapseclient as sc
from synapseclient import Evaluation

EMAIL = "santhosh.parampottupadam@dkfz-heidelberg.de"
API_KEY = ""


base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'subm_logs')
tasks = [("pixel", 9614846), ("sample", 9614847)]


def sync_mood_dir():
    try:
        copy_str = "rsync -Orav -e 'ssh -i /home/david/.ssh/id_rsa' --include '*/' --include='*.json'  --include='*.txt' --exclude='*' zimmerer@e132-comp04:/gpu/checkpoints/OE0441/zimmerer/logs/mood21/ /data/logs/mood21/"
        subprocess.run(
            shlex.split(copy_str),
            check=True,
        )
    except Exception as e:
        print("Syncing files changed")
        print(e)


def get_username_by_id(id, syn):
    rest_dict = syn.restGET(f"/userProfile/{id}")
    return rest_dict["userName"]


def process_submission(subm, task_name, task_dir):
    subm_user = subm["userId"]
    subm_id = subm["id"]
    subm_docker_name = subm["dockerRepositoryName"]
    subm_username = get_username_by_id(subm_user, syn)
    subm["username"] = subm_username

    subm_dir = os.path.join(task_dir, str(subm_id))

    # if os.path.exists(subm_dir):
    #     return

    print(f"\n\nProcessing submission from {subm_username} for the {task_name} task")

    # 3. run on cluster

    # task_name = "sample"

    cluster_cmd = (
        f"bsub -gpu num=1:j_exclusive=yes:mode=exclusive_process:gmem=10.7G -m gpu-titanxp-12gb -q gpu "
        f"'python /home/zimmerer/ws/PyTut/mood/private/run_image_all_in_one.py -s {subm_id} "
        f"-m {task_name}' "
    )

    cluster_cmd = cluster_cmd.replace("'", '\\"')
    shell_cmd = (
        f"ssh -i /home/david/.ssh/id_rsa zimmerer@odcf-lsf01.dkfz.de 'bash -lc \"sh cluster_run.sh {cluster_cmd} \"'"
    )

    print("Executing Image on Cluster...")
    subprocess.call(shell_cmd, shell=True)

    print(cluster_cmd)
    print(shell_cmd)


if __name__ == "__main__":

    subm_logs_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'subm_logs')

    subm_dict = {}
    subm_dict_path = os.path.join(subm_logs_path, "subm_dict.json")

    if os.path.exists(subm_dict_path):
        with open(subm_dict_path, "r") as fp_:
            subm_dict = json.load(fp_)
            # json.load(fp_)

    open_list = []

    for s_id, s_state in subm_dict.items():
        if s_state == "open":
            open_list.append(s_id)

    while True:

        # client = docker.from_env()
        syn = sc.login(email=EMAIL, apiKey=API_KEY)
        # evaluation = syn.store(Evaluation(
        #     name="Q1 Final",
        #     description="Predict progression of MMSE scores for final scoring",
        #     contentSource="syn28532982"))

        print("\nChecking for new submissions...")
        for task_name, task_id in tasks:
            print(f"Checking {task_name}...")

            task_dir = os.path.join(base_dir, task_name)
            for subm in syn.getSubmissions(task_id):
                if subm["id"] not in subm_dict:
                    process_submission(subm, task_name, task_dir)
                    subm_dict[subm["id"]] = "open"
                    open_list.append(subm["id"])

                    time.sleep(60)

        print("\nSynching results...")  # TODO !!!!!
        sync_mood_dir()

        print("Checking open tasks...")
        open_list_copy = open_list.copy()
        for s_id in open_list_copy:
            if os.path.exists(os.path.join(subm_logs_path, "sample", s_id, "end.txt")) or os.path.exists(
                os.path.join(subm_logs_path, "pixel", s_id, "end.txt")
            ):
                subm_dict[s_id] = "finished"
                open_list.remove(s_id)

        print("Saving submission dict...")
        with open(subm_dict_path, "w") as fp_:
            json.dump(subm_dict, fp_)

        print("\nTaking (coffee) a break now...")
        time.sleep(60 * 60 * 1)