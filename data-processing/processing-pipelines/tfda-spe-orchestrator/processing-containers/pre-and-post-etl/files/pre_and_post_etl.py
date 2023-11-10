import os
import subprocess
from subprocess import PIPE
from pathlib import Path
from os import getenv


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
    print("No operation, only placeholder...")


def algo_pre_etl():
    print("Prepare algorithm before being loaded into the isolated environment...")
    print("Downloading requested container from registry...")
    container_registry_url = getenv("CONTAINER_REGISTRY_URL", None)
    container_registry_user = getenv("CONTAINER_REGISTRY_USER", None)
    container_registry_pwd = getenv("CONTAINER_REGISTRY_PWD", None)
    container_name_version = getenv("CONTAINER_NAME_VERSION", None)
    container_name = container_name_version.split(":")[0]
    user_container_path = os.path.join(workflow_dir, "algorithm_files", container_name)
    Path(user_container_path).mkdir(parents=True, exist_ok=True)
    if (
        container_registry_user is None
        or container_registry_pwd is None
        or container_registry_user == ""
        or container_registry_pwd == ""
    ):
        print("Registry login credentials missing, skipping login...")
    else:
        print("Logging into container registry...")
        command = [
            "skopeo",
            "login",
            "--username",
            f"{container_registry_user}",
            "--password",
            f"{container_registry_pwd}",
            f"{container_registry_url}",
        ]
        return_code = run_command(command=command)
        if return_code == 0:
            print(f"Login to the registry successful!!")
        else:
            raise Exception("Login to the registry FAILED! Cannot proceed further...")

    print(f"Pulling container: {container_name_version}...")
    tarball_file = os.path.join(user_container_path, f"{container_name}.tar")
    if os.path.exists(tarball_file):
        print(
            f"Submission tarball already exists locally... deleting it now to pull latest!!"
        )
        os.remove(tarball_file)
    ## Due to absence of /etc/containers/policy.json in Airflow container, following Skopeo command only works with "--insecure-policy"
    command2 = [
        "skopeo",
        "--insecure-policy",
        "copy",
        f"docker://{container_registry_url}/{container_name_version}",
        f"docker-archive:{tarball_file}",
        "--additional-tag",
        f"{container_name_version}",
    ]
    return_code2 = run_command(command=command2)
    if return_code2 != 0:
        raise Exception(f"Error while trying to download container! Exiting...")


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
if getenv("ETL_STAGE") == "pre":
    algo_pre_etl()
else:
    post_etl()
