import os
import subprocess
from subprocess import PIPE
from pathlib import Path
from os import getenv
from typing import Tuple


def execute_shell_command(
    command, shell=False, blocking=True, timeout=5, skip_check=False
) -> Tuple[bool, str]:
    """Code copied from kaapana/services/kaapana-admin/kube-helm/docker/files/backend/app/helm_helper.py
    Runs given command via subprocess.run or subprocess.Popen

    Args:
        command (_type_): _description_
        shell (bool, optional): _description_. Defaults to False.
        blocking (bool, optional): _description_. Defaults to True.
        timeout (int, optional): _description_. Defaults to 5.

    Returns:
        success (bool)  : whether the command ran successfully
        stdout  (str)   : output of the command. If success=False it is the same as stderr
    """
    if blocking is False:
        print(f"running non-blocking {command=} via Popen, shell=True, timeout ignored")
        p = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        print(f"{p.pid=}")
        # TODO: add to a process queue, run p.communicate() & fetch returncode
        return True, ""

    print(f"executing blocking shell command: {command}")
    print(f"{shell=} , {timeout=}")
    if "--timeout" in command:
        print("--timeout found in command, not passing a separate timeout")
        timeout = None
    if shell == False:
        command = [x for x in command.replace("  ", " ").split(" ") if x != ""]
    command_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=shell,
        timeout=timeout,
    )

    stdout = command_result.stdout.strip()
    stderr = command_result.stderr.strip()
    return_code = command_result.returncode
    success = True if return_code == 0 and stderr == "" else False

    if success:
        print(f"Command successfully executed {command}")
        print(f"{return_code=}")
        print(f"{stdout=}")
        print(f"{stderr=}")
        return success, stdout
    elif command[3] == "status":
        print(
            f"Ignoring error, since we just wanted to check if chart is installed {command}"
        )
        print(f"{return_code=}")
        print(f"{stdout=}")
        print(f"{stderr=}")
        return success, stderr
    else:
        print("ERROR while executing command: ")
        print(f"COMMAND: {command}")
        print("STDOUT:")
        for line in stdout.splitlines():
            print(f"{line}")
        print("")
        print("STDERR:")
        for line in stderr.splitlines():
            print(f"{line}")
        print("")
        return success, stderr


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
        command = f"skopeo login --username {container_registry_user} --password {container_registry_pwd} {container_registry_url}"
        success, stdout = execute_shell_command(
            command=command, shell=True, blocking=True, timeout=60
        )
        if success:
            print(f"Login to the registry successful!!")
        else:
            err = "Login to the registry FAILED! Cannot proceed further..."
            print(f"{err} {stdout=}")
            raise RuntimeError(err)
    print(f"Pulling container: {container_name_version}...")
    tarball_file = os.path.join(user_container_path, f"{container_name}.tar")
    if os.path.exists(tarball_file):
        print(
            f"Container tarball already exists locally... deleting it now to pull latest!!"
        )
        os.remove(tarball_file)
    ## Due to absence of /etc/containers/policy.json in Airflow container, following Skopeo command only works with "--insecure-policy"
    command2 = f"skopeo --insecure-policy copy docker://{container_registry_url}/{container_name_version} docker-archive:{tarball_file} --additional-tag {container_name_version}"
    success, stdout = execute_shell_command(
        command=command2, shell=True, blocking=True, timeout=60
    )
    if success:
        print("Download was successful!")
    if not success:
        err = "Error while trying to download! Exiting..."
        print(f"{err} {stdout=}")
        raise RuntimeError(err)


workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
if getenv("ETL_STAGE") == "pre":
    algo_pre_etl()
elif getenv("ETL_STAGE") == "post":
    post_etl()
else:
    raise RuntimeError(
        f"ETL stage type {getenv('ETL_STAGE')} not supported! Exiting..."
    )
