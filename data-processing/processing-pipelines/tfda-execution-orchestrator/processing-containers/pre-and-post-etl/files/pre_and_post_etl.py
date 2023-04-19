import os
import logging
import subprocess
import ast
from subprocess import PIPE
from pathlib import Path
from os import getenv

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
dag_run_id = getenv("RUN_ID")

def run_command(command):
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            print(output.strip())
    return_code = process.poll()
    return return_code

def post_etl():
    logging.info("No operation, only placeholder...")

def algo_pre_etl():
    logging.info("Prepare data and algorithm before being loaded into the isolated environment...")
    logging.debug("Downloading container from registry since container workflow is requested...")
    container_registry_url = getenv('CONTAINER_REGISTRY_URL', "None")
    container_registry_user = getenv('CONTAINER_REGISTRY_USER', "None")
    container_registry_pwd = getenv('CONTAINER_REGISTRY_PWD', "None")
    container_name_version = getenv('CONTAINER_NAME_VERSION', "None")
    container_name = container_name_version.split(":")[0]
    user_experiment_path = os.path.join(workflow_dir, "algorithm_files", container_name)
    Path(user_experiment_path).mkdir(parents=True, exist_ok=True)
    logging.info("Logging into container registry...")
    command = ["skopeo", "login", "--username", f"{container_registry_user}", "--password", f"{container_registry_pwd}", f"{container_registry_url}"]
    return_code = run_command(command=command)
    if return_code == 0:
        logging.info(f"Login to the registry successful!!")
    else:
        raise Exception("Login to the registry FAILED! Cannot proceed further...")

    logging.debug(f"Pulling container: {container_name_version}...")
    tarball_file = os.path.join(user_experiment_path, f"{container_name}.tar")
    if os.path.exists(tarball_file):
        logging.debug(f"Submission tarball already exists locally... deleting it now to pull latest!!")
        os.remove(tarball_file)
    ## Due to absence of /etc/containers/policy.json in Airflow container, following Skopeo command only works with "--insecure-policy"
    command2 = ["skopeo", "--insecure-policy", "copy", f"docker://{container_registry_url}/{container_name_version}", f"docker-archive:{tarball_file}", "--additional-tag", f"{container_name_version}"]
    return_code2 = run_command(command=command2)
    if return_code2 != 0:
        raise Exception(f"Error while trying to download container! Exiting...")

logging.info("##################################################")
logging.info("#")
logging.info("# Starting operator dice-evaluation:")
logging.info("#")
logging.info(f"# workflow_dir:     {workflow_dir}")
logging.info("#")
logging.info(f"# dag_run_id:     {dag_run_id}")
logging.info("#")

if getenv("ETL_STAGE") == "pre":
    algo_pre_etl()
else:
    post_etl()