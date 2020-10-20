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


def helm_show_values(repo, name, version):
    try:
        chart = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} show values {app.config["HELM_REPOSITORY_CACHE"]}/{name}-{version}.tgz', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print('Nothing found!')
        return {}
    return yaml.load(chart)


def helm_show_chart(repo, name, version):
    try:
        chart = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} show chart {app.config["HELM_REPOSITORY_CACHE"]}/{name}-{version}.tgz', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print('Nothing online, nothing local!')      
        return {}
    return yaml.load(chart)


def helm_get_manifest(release_name, namespace):
    try:
        manifest = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {namespace} get manifest {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return []
    return list(yaml.load_all(manifest))    


def helm_get_values(release_name, namespace):
    try:
        values = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {namespace} get values -o json {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return dict()
    if values==b'null\n':
        return dict()
    return json.loads(values)


def helm_status(release_name, namespace):
    try:
        status = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {namespace} status {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return dict()
    return yaml.load(status)


def helm_prefetch_extension_docker():
    regex = r'image: ([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)'
    extensions = helm_search_repo("(kaapanaextension|kaapanaint|kaapanadag)")
    dags = []
    for extension in extensions:
        repo_name, chart_name = extension["name"].split('/')
        print(chart_name, extension["version"], f'{app.config["HELM_REPOSITORY_CACHE"]}/{chart_name}-{extension["version"]}.tgz')
        if os.path.isfile(f'{app.config["HELM_REPOSITORY_CACHE"]}/{chart_name}-{extension["version"]}.tgz') is not True:
            print(f'{extension["name"]} not found')
            continue
        chart = helm_show_chart(repo_name, chart_name, extension['version'])
        print(chart)
        payload = {
            'name': extension["name"],
            'version': extension["version"],
            'keywords': chart["keywords"],
            'release_name': f'prefetch-{chart_name}'
            }

        if 'kaapanaexperimental' in chart["keywords"]:
            continue
            print(f'Skipping {extension["name"]}, since its experimental')
        elif 'kaapanadag' in chart["keywords"]:
            dags.append(payload)
        else:
            print(f'Prefetching {extension["name"]}')
            try:
                release, _ = helm_install(payload, app.config["NAMESPACE"], helm_command_addons='--dry-run', in_background=False)
                manifest = json.loads(release.decode("utf-8"))["manifest"]
                matches = re.findall(regex, manifest)
                if matches:
                    for match in matches:
                        docker_registry_url = match[0]
                        docker_registry_project = match[1]
                        docker_image = match[2]
                        docker_version = match[3]
                        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
                        try:
                            pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, docker_registry_project)
                        except subprocess.CalledProcessError as e:
                            helm_delete(release_name, app.config['NAMESPACE'])
                            print(e)
            except subprocess.CalledProcessError as e:
                print(f'Skipping {extension["name"]} due to {e.output.decode("utf-8")}')
    for dag in dags:
        try:
            print(f'Prefetching {dag["name"]}')
            dag['sets'] = {
                'action': 'prefetch'
            }
            helm_comman_suffix = f'--wait --atomic --timeout=120m0s; sleep 10;{os.environ["HELM_PATH"]} delete --no-hooks -n {app.config["NAMESPACE"]} {dag["release_name"]}'
            helm_install(dag, app.config["NAMESPACE"], helm_comman_suffix=helm_comman_suffix)
        except subprocess.CalledProcessError as e:
            print(f'Skipping {dag["name"]} due to {e.output.decode("utf-8")}')
            helm_delete(dag['release_name'], app.config['NAMESPACE'], helm_command_addons='--no-hooks')


def pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, docker_registry_project, timeout='120m0s'):
    print(f'Pulling {docker_registry_url}{docker_registry_project}/{docker_image}:{docker_version}')   
    payload = {
        'name': f'{app.config["CHART_REGISTRY_PROJECT"]}/pull-docker-chart',
        'version': f'{app.config["VERSION"]}',
        'sets': {
            'registry_url': docker_registry_url or os.getenv('REGISTRY_URL'),
            'registry_project': docker_registry_project or os.getenv('REGISTRY_PROJECT'),
            'image': docker_image,
            'version': docker_version
        },
        'release_name': release_name
    }

    helm_comman_suffix = f'--wait --atomic --timeout {timeout}; sleep 10;{os.environ["HELM_PATH"]} delete -n {app.config["NAMESPACE"]} {release_name}'
    helm_install(payload, app.config["NAMESPACE"], helm_comman_suffix=helm_comman_suffix)


def helm_install(payload, namespace, helm_command_addons='', helm_comman_suffix='', in_background=True):

    repo_name, chart_name = payload["name"].split('/')
    version = payload["version"]

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
    
    values = helm_show_values(repo_name, chart_name, version)
    
    if 'keywords' not in payload:
        chart = helm_show_chart(repo_name, chart_name, version)
        if 'keywords' in chart:
            keywords = chart['keywords']
        else:
            keywords = []
    else:
        keywords = payload['keywords']

    if 'global' in values:
        for key, value in values['global'].items():
            if value != '':
                default_sets.update({f'global.{key}': value })
    
    if 'sets' not in payload:
        payload['sets'] = default_sets
    else: 
        for key, value in default_sets.items():
            if key not in payload['sets'] or payload['sets'][key] == '':
                payload['sets'].update({key: value})

    if "release_name" in payload:
        release_name = payload["release_name"]
    elif 'kaapanamultiinstallable' in keywords:
        release_name = f'{chart_name}-{secrets.token_hex(10)}'
    else:
        release_name = chart_name

    status = helm_status(release_name, namespace)
    if status:
        chart = helm_show_chart(repo_name, chart_name, version)
        if 'keywords' in chart and 'kaapanamultiinstallable' in chart['keywords']:
            print('Installing again since its kaapanamultiinstallable')
        else:
            return "already installed", 'no_helm_command'

    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            helm_sets = helm_sets + f" --set {key}='{value}'"

    helm_command = f'{os.environ["HELM_PATH"]} install {helm_command_addons} -n {namespace} {release_name} {helm_sets} {app.config["HELM_REPOSITORY_CACHE"]}/{chart_name}-{version}.tgz -o json {helm_comman_suffix}'
    print('helm_command', helm_command)
    if in_background is False:
        return subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command
    else:
        return subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command


def helm_delete(release_name, namespace, helm_command_addons=''):
    helm_command = f'{os.environ["HELM_PATH"]} delete {helm_command_addons} -n {namespace} {release_name}'
    subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)


def helm_ls(namespace, release_filter=''):
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {namespace} --filter {release_filter} ls --deployed --pending --failed --uninstalling -o json', stderr=subprocess.STDOUT, shell=True)
        return json.loads(resp)
    except subprocess.CalledProcessError as e:
        return []
        

def helm_search_repo(filter_regex):
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} search repo --devel -l -r "{filter_regex}" -o json', stderr=subprocess.STDOUT, shell=True
            )
        
        data = json.loads(resp)
    except subprocess.CalledProcessError as e:
        print('Error calling search repo!', e.output)
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
    ingress_paths = []
    
    concatenated_states = {
        "name": [], 
        "ready": [],
        "status": [],
        "restarts": [],
        "age": []
    }


    for config in manifest:
        ingress_path = ''
        if config['kind'] == 'Ingress':
            ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
            ingress_paths.append(ingress_path)
        if config['kind'] == 'Deployment':
            kube_status = get_kube_status('app', config['spec']['selector']['matchLabels']['app-name'], config['metadata']['namespace'])
            for key, value in kube_status.items():
                concatenated_states[key]  = concatenated_states[key] + value
        if config['kind'] == 'Job':
            kube_status = get_kube_status('job',config['metadata']['name'], config['metadata']['namespace'])
            for key, value in kube_status.items():
                concatenated_states[key]  = concatenated_states[key] + value

    return concatenated_states, ingress_paths


def all_successful(status):
    successfull = ['Completed', 'Running', 'deployed']
    for i in status:
        if i not in successfull:
            return 'no'
    return 'yes'