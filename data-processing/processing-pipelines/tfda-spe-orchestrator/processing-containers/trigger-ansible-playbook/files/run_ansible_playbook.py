import os
import re
import json
import subprocess
from subprocess import PIPE
from os import getenv
from pathlib import Path


def load_config(config_filepath):
    with open(config_filepath, "r") as stream:
        try:
            config_dict = json.load(stream)
            return config_dict
        except Exception as exc:
            raise Exception(f"Could not extract configuration due to error: {exc}!!")


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


def manage_iso_inst():
    instance_state = getenv("INSTANCE_STATE", None)
    if instance_state == "present":
        print("Starting an isolated environment...")
    elif instance_state == "absent":
        print("Deleting isolated environment...")

    playbook_path = os.path.join(
        playbooks_dir, "manage_" + platform_name + "_instance.yaml"
    )
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")

    playbook_args = f"instance_name={workflow_type}_instance instance_state={instance_state} ssh_key_operator_path={ssh_key_operator_path}"

    if platform_name in ["openstack", "qemu_kvm"]:
        for key, value in platform_config["platforms"][platform_name][
            "platform_flavors"
        ][flavor_name].items():
            playbook_args += f" {key}={value}"
    else:
        raise Exception(
            f"Sorry!! {platform_name.title()} is not yet supported. Please choose a supported platform..."
        )

    if platform_name in "qemu_kvm":
        vault_text_file = platform_config["platforms"][platform_name][
            "platform_flavors"
        ][flavor_name]["vault_text_file"]
        vault_filepath = os.path.join(playbooks_dir, vault_text_file)
        vm_config_container_path = os.path.join(workflow_dir, "KVM_config_files")
        try:
            os.makedirs(vm_config_container_path)
        except FileExistsError:
            pass
        ssh_key_container_path = "/root/.ssh"
        playbook_args += f" vm_config_container_path={vm_config_container_path} ssh_key_container_path={ssh_key_container_path}"
        if not os.path.isfile(vault_filepath):
            raise Exception(
                f"Vault file {vault_filepath} for password not found in playbooks directory, please create it first!"
            )
        command = [
            "ansible-playbook",
            f"--vault-password-file={vault_filepath}",
            playbook_path,
            "--extra-vars",
            playbook_args,
        ]
    else:
        command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            print(output.strip())
            ip_addr_str_search = re.findall(
                r"isolated_env_ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", output
            )
            if instance_state == "present" and ip_addr_str_search:
                ip_addr_string = re.findall(
                    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", output
                )
                print(f"IP address of new isolated instance is: {ip_addr_string[-1]}")
                with open(iso_env_ip_path, "w+") as f:
                    f.write(ip_addr_string[-1])
    rc = process.poll()
    if rc == 0:
        print(f"Iso instance managed successfully!")
    else:
        raise Exception("Failed to manage isolated environment!")


def setup_vnc_server():
    print("Setup a VNC service inside the isolated environment...")
    playbook_path = os.path.join(playbooks_dir, "setup_vnc_server.yaml")
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")

    with open(iso_env_ip_path, "r") as file:
        iso_env_ip = file.read().rstrip()
    playbook_args = f"target_host={iso_env_ip} ssh_key_operator_path={ssh_key_operator_path} ssh_key_name={ssh_key_name} remote_username={remote_username}"
    command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    rc = run_command(command=command)
    if rc == 0:
        print(f"VNC server setup successfully!!")
    else:
        raise Exception("Playbook FAILED! Cannot proceed further...")


def copy_data_algo():
    print("Copy data and algorithm to isolated environment...")
    playbook_path = os.path.join(playbooks_dir, "copy_data_and_algo_to_iso_env.yaml")
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")
    container_name_version = getenv("CONTAINER_NAME_VERSION", None)
    pacs_batch_name = getenv("BATCH_NAME", None)
    pacs_data_path = os.path.join(workflow_dir, pacs_batch_name)
    container_name = container_name_version.split(":")[0]
    user_container_path = os.path.join(workflow_dir, "algorithm_files", container_name)
    src_data_path = os.path.join(workflow_dir, data_dir_name)

    with open(iso_env_ip_path, "r") as file:
        iso_env_ip = file.read().rstrip()
    playbook_args = f"target_host={iso_env_ip} ssh_key_operator_path={ssh_key_operator_path} ssh_key_name={ssh_key_name} remote_username={remote_username} \
                        workflow_type={workflow_type} src_algorithm_files_path={user_container_path} \
                        user_experiment_name={container_name} src_data_path={src_data_path} \
                        user_selected_data={data_dir_name} pacs_data_path={pacs_data_path}"
    command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    rc = run_command(command=command)
    if rc == 0:
        print(f"Files copied successfully!!")
    else:
        raise Exception("Playbook FAILED! Cannot proceed further...")


def run_isolated_workflow():
    print("Run algorithm in isolated environment...")
    playbook_path = os.path.join(playbooks_dir, f"run_{workflow_type}.yaml")
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")
    container_name_version = getenv("CONTAINER_NAME_VERSION", None)
    container_name = container_name_version.split(":")[0]
    with open(iso_env_ip_path, "r") as file:
        iso_env_ip = file.read().rstrip()
    playbook_args = f"target_host={iso_env_ip} ssh_key_operator_path={ssh_key_operator_path} ssh_key_name={ssh_key_name} \
                    user_experiment_name={container_name} user_selected_data={data_dir_name} user_container_name_version={container_name_version} remote_username={remote_username}"
    command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    rc = run_command(command=command)
    if rc == 0:
        print(f"Algorithm ran successfully!!")
    else:
        raise Exception("Playbook FAILED! Cannot proceed further...")


def fetch_results():
    operator_out_dir = getenv("OPERATOR_OUT_DIR", None)
    operator_out_dir = operator_out_dir if operator_out_dir.lower() != "none" else None
    assert operator_out_dir is not None
    print("Fetching results from isolated execution environment...")
    playbook_path = os.path.join(playbooks_dir, "fetch_results.yaml")
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")
    container_name_version = getenv("CONTAINER_NAME_VERSION", None)
    container_name = container_name_version.split(":")[0]
    with open(iso_env_ip_path, "r") as file:
        iso_env_ip = file.read().rstrip()
    results_path = os.path.join(workflow_dir, operator_out_dir)
    Path(ssh_key_operator_path).mkdir(parents=True, exist_ok=True)
    playbook_args = f"target_host={iso_env_ip} ssh_key_operator_path={ssh_key_operator_path} ssh_key_name={ssh_key_name} \
                    user_experiment_name={container_name} user_selected_data={data_dir_name} user_container_name_version={container_name_version} results_path={results_path} remote_username={remote_username}"
    command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    rc = run_command(command=command)
    if rc == 0:
        print(f"Results were fetched successfully!!")
    else:
        raise Exception("Playbook FAILED! Cannot proceed further...")


workflow_dir = getenv("WORKFLOW_DIR", None)
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
data_dir_name = "user-selected-data"
platform_config_path = os.path.join(workflow_dir, "platform_config.json")
platform_config = load_config(platform_config_path)
## Currently, hard coded to only container based workflows
workflow_type = "container_workflow"
platform_name = platform_config["default_platform"][workflow_type]
flavor_name = platform_config["platforms"][platform_name]["default_flavor"][
    workflow_type
]
home_dir = os.path.dirname(os.path.abspath(__file__))
playbooks_dir = os.path.join(home_dir, "ansible-playbooks")
iso_env_ip_path = os.path.join(workflow_dir, "iso_env_ip.txt")
ssh_key_name = platform_config["platforms"][platform_name]["platform_flavors"][
    flavor_name
]["ssh_key_name"]
remote_username = platform_config["platforms"][platform_name]["platform_flavors"][
    flavor_name
]["remote_username"]
container_name_version = getenv("CONTAINER_NAME_VERSION", None)
container_name = container_name_version.split(":")[0]
ssh_key_operator_path = os.path.join(workflow_dir, ".ssh")
Path(ssh_key_operator_path).mkdir(parents=True, exist_ok=True)
task_type = getenv("TASK_TYPE", None)
task_type = task_type if task_type.lower() != "none" else None
assert task_type is not None
if task_type in ["create-iso-inst", "delete-iso-inst"]:
    manage_iso_inst()
elif task_type == "setup-vnc-server":
    setup_vnc_server()
elif task_type == "copy-data-algo":
    copy_data_algo()
elif task_type == "run-isolated-workflow":
    run_isolated_workflow()
elif task_type == "fetch-results":
    fetch_results()
