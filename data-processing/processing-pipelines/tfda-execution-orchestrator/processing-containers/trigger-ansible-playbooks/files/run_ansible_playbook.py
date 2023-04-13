import os
import logging
import re
import ast
import subprocess
from subprocess import PIPE
from os import getenv

workflow_dir = getenv("WORKFLOW_DIR", "None")
workflow_dir = workflow_dir if workflow_dir.lower() != "none" else None
assert workflow_dir is not None
dag_run_id = getenv("RUN_ID")

# operator_in_dir = getenv("OPERATOR_IN_DIR", "None")
# operator_in_dir = operator_in_dir if operator_in_dir.lower() != "none" else None
# assert operator_in_dir is not None

def manage_iso_inst(iso_env_ip_path):
    instance_state = getenv("INSTANCE_STATE", "None")
    if instance_state == "present":
        logging.info("Starting an isolated environment...")
    elif instance_state == "absent":
        logging.info("Deleting isolated environment...")

    platform_config = getenv("PLATFORM_CONFIG", "None")
    platform_config = platform_config if platform_config.lower() != "none" else None
    assert platform_config is not None
    platform_config = ast.literal_eval(platform_config)
    ## Currently, hard coded to only container based workflows
    workflow_type = "container_workflow"
    platform_name = platform_config["default_platform"][workflow_type]
    flavor_name = platform_config["platforms"][platform_name]["default_flavor"][workflow_type]
    home_dir = os.path.dirname(os.path.abspath(__file__))
    playbooks_dir = os.path.join(home_dir, "ansible-playbooks")
    playbook_path = os.path.join(playbooks_dir, "manage_"+platform_name+"_instance.yaml")
    if not os.path.isfile(playbook_path):
        raise Exception(f"Playbook '{playbook_path}' file not found!")

    playbook_args = f"instance_name={workflow_type}_instance instance_state={instance_state}"
    
    if platform_name in ["openstack", "qemu_kvm"]:
        for key, value in platform_config["platforms"][platform_name]["platform_flavors"][flavor_name].items():
            playbook_args += f" {key}={value}"
    else:
        raise Exception(f"Sorry!! {platform_name.title()} is not yet supported. Please choose a supported platform...")
    
    if platform_name in "qemu_kvm":
        vault_text_file = platform_config["platforms"][platform_name]["platform_flavors"][flavor_name]["vault_text_file"]
        vault_filepath = os.path.join(playbooks_dir, vault_text_file)
        vm_config_container_path = os.path.join(workflow_dir, "KVM_config_files")
        try:
            os.makedirs(vm_config_container_path)
        except FileExistsError:
            # directory already exists
            pass
        ssh_key_container_path = "/root/.ssh"
        playbook_args += f" vm_config_container_path={vm_config_container_path} ssh_key_container_path={ssh_key_container_path}"
        if not os.path.isfile(vault_filepath):
            raise Exception(f"Vault file {vault_filepath} for password not found in playbooks directory, please create it first!")
        command = ["ansible-playbook", f"--vault-password-file={vault_filepath}", playbook_path, "--extra-vars", playbook_args]
    else:
        command = ["ansible-playbook", playbook_path, "--extra-vars", playbook_args]
    process = subprocess.Popen(command, stdout=PIPE, stderr=PIPE, encoding="Utf-8")
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            print(output.strip())
            ip_addr_str_search = re.findall(r'isolated_env_ip: \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
            if instance_state == "present" and ip_addr_str_search:
                ip_addr_string = re.findall(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', output)
                logging.info(f"IP address of new isolated instance is: {ip_addr_string[-1]}")
                with open(iso_env_ip_path, "w+") as f:
                    f.write(ip_addr_string[-1])
    rc = process.poll()
    if rc == 0:
        logging.info(f'Iso instance managed successfully!')
    else:
        raise Exception("Failed to manage isolated environment!")

logging.info("##################################################")
logging.info("#")
logging.info("# Starting operator dice-evaluation:")
logging.info("#")
logging.info(f"# workflow_dir:     {workflow_dir}")
logging.info("#")
logging.info(f"# dag_run_id:     {dag_run_id}")
logging.info("#")
# logging.info(f"# operator_in_dir:  {operator_in_dir}")
iso_env_ip_path = os.path.join(workflow_dir, "iso_env_ip.txt")
manage_iso_inst(iso_env_ip_path)
