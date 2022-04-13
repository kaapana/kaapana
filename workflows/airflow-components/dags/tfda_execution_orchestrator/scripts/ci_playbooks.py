#!/usr/bin/python3

import os
import ci_playbook_execute
import json
from pathlib import Path

kaapana_home = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
)


def start_os_instance(
    username,
    password,
    project_name,
    project_id,
    instance_name="kaapana-deploy-instance",
    os_image="ubuntu",
    volume_size="90",
    instance_flavor="dkfz-8.16",
    ssh_key="kaapana",
    suite_name="Setup Test Server",
):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/00_start_openstack_instance.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "os_project_name": project_name,
        "os_project_id": project_id,
        "os_instance_name": instance_name,
        "os_username": username,
        "os_password": password,
        "os_image": os_image,
        "os_ssh_key": ssh_key,
        "os_volume_size": volume_size,
        "os_instance_flavor": instance_flavor,
    }

    instance_ip_address, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="Start OpenStack instance: {}".format(os_image),
        hosts=["localhost"],
        extra_vars=extra_vars,
    )

    return instance_ip_address, logs


def start_install_server_dependencies(
    target_hosts, remote_username, local_script=False, suite_name="Setup Test Server"
):

    # """playbook_path = os.path.join(
    # kaapana_home, "CI/ansible_playbooks/01_install_server_dependencies.yaml"
    # )"""
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/01_change_hostname.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {"remote_username": remote_username, "local_script": local_script}

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="Change hostname",
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def deploy_platform(
    target_hosts,
    remote_username,
    registry_user,
    registry_pwd,
    registry_url,
    local_script=False,
    platform_name="Kaapana",
    suite_name="Test Platform",
):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/02_deploy_platform.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "remote_username": remote_username,
        "registry_user": registry_user,
        "registry_pwd": registry_pwd,
        "registry_url": registry_url,
        "local_script": local_script,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="{0: <14}: Deploy platform".format(platform_name),
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def copy_data_algo(
    target_hosts,
    remote_username,
    bucket_name,
    chart_path,
    chart_filename,
    suite_name="Copy Data Algorithm to Iso env",
):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/copy_data_algo_to_iso_env.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "bucket_name": bucket_name,
        "chart_path": chart_path,
        "chart_filename": chart_filename,
        "remote_username": remote_username,
        # "registry_user": registry_user,
        # "registry_pwd": registry_pwd,
        # "registry_url" : registry_url,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="Copy Data and Algorithm to Isolated Environment",
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def run_algo_and_send_result(
    target_hosts,
    remote_username,
    chart_filename,
    suite_name="Run Algo and Send results",
):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/run_algo_send_result.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        # "bucket_name" : bucket_name,
        "chart_filename": chart_filename,
        "remote_username": remote_username,
        # "registry_user": registry_user,
        # "registry_pwd": registry_pwd,
        # "registry_url" : registry_url,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="Copy Data and Algorithm to Isolated Environment",
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def delete_platform_deployment(target_hosts, platform_name, suite_name="Test Platform"):
    global instance_ip_address

    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/03_delete_deployment.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "KAAPANA_HOME": kaapana_home,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="{0: <14}: Delete platform".format(platform_name),
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def purge_filesystem(target_hosts, platform_name="Kaapana", suite_name="Test Platform"):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/04_purge_filesystem.yaml"
    )
    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "server_domain": "",
        "KAAPANA_HOME": kaapana_home,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="{0: <14}: Purge filesystem from".format(platform_name),
        hosts=target_hosts,
        extra_vars=extra_vars,
    )
    return return_value, logs


def delete_os_instance(
    username,
    password,
    os_project_name,
    os_project_id,
    instance_name="kaapana-instance",
    suite_name="Setup Test Server",
):
    playbook_path = os.path.join(
        kaapana_home, "CI/ansible_playbooks/05_delete_os_instance.yaml"
    )

    if not os.path.isfile(playbook_path):
        print("playbook yaml not found.")
        exit(1)

    extra_vars = {
        "os_project_name": os_project_name,
        "os_project_id": os_project_id,
        "os_username": username,
        "os_password": password,
        "os_instance_name": instance_name,
    }

    return_value, logs = ci_playbook_execute.execute(
        playbook_path,
        testsuite=suite_name,
        testname="Delete OpenStack instance",
        hosts=["localhost"],
        extra_vars=extra_vars,
    )
    return return_value, logs


if __name__ == "__main__":
    print("File execution is not supported at the moment")
    exit(1)
