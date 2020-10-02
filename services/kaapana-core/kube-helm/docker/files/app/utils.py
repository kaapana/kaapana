import os
import yaml
import functools
import secrets
import re
import json
import time
import requests
import subprocess, json
from flask import render_template, Response, request, jsonify
from app import app


def internet_access_decorator(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        print('Checking internet access')   
        r = requests.get('https://dktk-jip-registry.dkfz.de/api/v2.0/projects')
        return func(*args, **kwargs)

    return wrapper_decorator


def helm_repo_update_decorator(func):
    @functools.wraps(func)
    def wrapper_decorator(*args, **kwargs):
        print('Executing repo udpate')
        try:
            repoUpdated = subprocess.check_output(
                [os.environ["HELM_PATH"], "repo", "update"], stderr=subprocess.STDOUT
            )
        except subprocess.CalledProcessError as e:
            print('Repo update failed due to missing internet connection or wrong credentials: ', e)
            pass 

        return func(*args, **kwargs)
    return wrapper_decorator


def helm_show_values(repo, name, version):
    try:
        chart = subprocess.check_output(
            [os.environ["HELM_PATH"], "show", "values", f"--version={version}", f"{repo}/{name}"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return {}
    return yaml.load(chart)


def helm_show_chart(repo, name, version):
    try:
        chart = subprocess.check_output(
            [os.environ["HELM_PATH"], "show", "chart", f"--version={version}", f"{repo}/{name}"], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return {}
    return yaml.load(chart)


def helm_get_manifest(release_name, namespace):
    try:
        manifest = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "get", "manifest", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return []
    return list(yaml.load_all(manifest))    


def helm_get_values(release_name, namespace):
    try:
        values = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "get", "values", "-o", "json", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return dict()
    if values==b'null\n':
        return dict()
    return json.loads(values)


def helm_status(release_name, namespace):
    try:
        status = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "status", release_name], stderr=subprocess.STDOUT
        )
    except subprocess.CalledProcessError as e:
        return dict()
    return yaml.load(status)


@internet_access_decorator
def pull_docker_image(docker_image, docker_version, docker_registry_url='dktk-jip-registry.dkfz.de', docker_registry_project='/kaapana', timeout='120m0s'):
    print(f'Pulling {docker_registry_url}{docker_registry_project}/{docker_image}:{docker_version}')
    repoName = 'kaapana-public'
    chartName = 'pull-docker-chart'
    version = '1.0-vdev'
    release_name = f'{chartName}-{secrets.token_hex(10)}'
    sets = {
        'registry_url': docker_registry_url or os.getenv('REGISTRY_URL'),
        'registry_project': docker_registry_project or os.getenv('REGISTRY_PROJECT'),
        'image': docker_image,
        'version': docker_version
    }

    helm_sets = ''
    for key, value in sets.items():
        helm_sets = helm_sets + f" --set {key}='{value}'"
    helm_command = f'{os.environ["HELM_PATH"]} install -n {app.config["NAMESPACE"]} --version {version} {release_name} {helm_sets} {repoName}/{chartName} -o json --wait --atomic --timeout {timeout}'
    helm_command = helm_command + ';' +  f'{os.environ["HELM_PATH"]} delete -n {app.config["NAMESPACE"]} {release_name}'
    print('helm_command', helm_command) 
    try:
        resp = subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)
        return Response(f"We are trying to download the docker container {docker_registry_url}{docker_registry_project}/{docker_image}:{docker_version}", 202)
    except subprocess.CalledProcessError as e:
        helm_delete(release_name,       {
        text: "Helm Status",
        align: "start",
        value: "status",
      }, app.config['NAMESPACE'])
        print(e)
        return Response(
            f"We could not download your container",
            500
        )


def helm_install(payload, namespace):

    repoName, chartName = payload["name"].split('/')
    version = payload["version"]

    values = helm_show_values(repoName, chartName, payload["version"])
    default_sets =  {
        'global.registry_url': os.getenv('REGISTRY_URL'),
        'global.registry_project': os.getenv('REGISTRY_PROJECT'),
        'global.base_namespace': os.getenv('BASE_NAMESPACE'),
        'global.flow_namespace': os.getenv('FLOW_NAMESPACE'),
        'global.flow_jobs_namespace': os.getenv('FLOW_JOBS_NAMESPACE'),
        'global.fast_data_dir': os.getenv('FAST_DATA_DIR'),
        'global.slow_data_dir': os.getenv('SLOW_DATA_DIR'),
        'global.pull_policy_pods': os.getenv('PULL_POLICY_PODS'),
        'global.pull_policy_jobs': os.getenv('PULL_POLICY_JOBS')
    } 
    for key, value in values['global'].items():
        if value != '':
            default_sets.update({f'global.{key}': value })
    
    if 'sets' not in payload:
        payload['sets'] = default_sets
    else: 
        for key, value in default_sets.items():
            if key not in payload['sets'] or payload['sets'][key] == '':
                payload['sets'].update({key: value})

    if "custom_release_name" in payload:
        release_name = payload["custom_release_name"]
    elif 'kaapanamultiinstallable' in payload["keywords"]:
        release_name = f'{chartName}-{secrets.token_hex(10)}'
    else:
        release_name = chartName

    status = helm_status(release_name, namespace)
    if status:
        chart = helm_show_chart(repoName, chartName, version)
        if 'keywords' in chart and 'kaapanamultiinstallable' in chart['keywords']:
            print('Installing again since its kaapanamultiinstallable')
        else:
            return Response(
                "installed",
                200,
            )

    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            helm_sets = helm_sets + f" --set {key}='{value}'"

    print(helm_sets)
    helm_command = f'{os.environ["HELM_PATH"]} install -n {namespace} --version {version} {release_name} {helm_sets} {repoName}/{chartName} -o json'
    print('helm_command', helm_command)

    try:
        resp = subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)
        
        return Response(f"Trying to install with {helm_command}", 200)
    except subprocess.CalledProcessError as e:
        return Response(
            f"A helm command error occured!",
            500,
        )


def helm_delete(release_name, namespace):
    try:
        print(f'deleting {release_name}')
        resp = subprocess.Popen(
            [os.environ["HELM_PATH"], "-n", namespace, "delete", release_name], stderr=subprocess.STDOUT
        )
        print(f'Successfully deleted {release_name}')
        return jsonify({"message": str(resp), "status": "200"})
    except subprocess.CalledProcessError as e:
        return Response(
            f"We could not find the release you are trying to delete!",
            500,
        )

def helm_ls(namespace, release_filter=''):
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "-n", namespace, "--filter", release_filter, "ls", "--deployed", "--pending", "--failed", "--uninstalling", "-o", "json"], stderr=subprocess.STDOUT
        )
        return json.loads(resp)
    except subprocess.CalledProcessError as e:
        return []
        
def helm_search_repo(filter_regex):
    try:
        resp = subprocess.check_output(
            [os.environ["HELM_PATH"], "search", "repo", "--devel", "-r", filter_regex, "-o", "json"],
            stderr=subprocess.STDOUT,
        )
        try:
            data = json.loads(resp)
            print(data)
        except json.decoder.JSONDecodeError as e:
            print('No results found', e)
            data = []
    except subprocess.CalledProcessError as e:
        print('Error calling repo search!')
        data = []
    return data

def get_kube_status(kind, name, namespace):
    states = {
        "name": [], 
        "ready": [],
        "status": [],
        "restarts": [],
        "age": []
    }

    try:
        resp = subprocess.check_output(
            f'kubectl -n {namespace} get pod -l={kind}-name={name}',
            stderr=subprocess.STDOUT,
            shell=True
        )
        for row in re.findall(r'(.*\n)', resp.decode("utf-8"))[1:]:
            name, ready, status, restarts, age = row.split()
            states['name'].append(name)
            states['ready'].append(ready)
            states['status'].append(status)
            states['restarts'].append(restarts)
            states['age'].append(age)
    except subprocess.CalledProcessError as e:
        print(f'Could not get kube status of {name}')

    return states

def get_manifest_infos(manifest):
    ingress_path = ''
    for config in manifest:
        if config['kind'] == 'Ingress':
            ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
        if config['kind'] == 'Deployment':
            kube_status = get_kube_status('app',config['metadata']['name'], config['metadata']['namespace'])
        if config['kind'] == 'Job':
            kube_status = get_kube_status('job',config['metadata']['name'], config['metadata']['namespace'])
    return kube_status, ingress_path

def all_successful(status):
    successfull = ['Completed', 'Running', 'deployed']
    for i in status:
        if i not in successfull:
            return 'no'
    return 'yes'