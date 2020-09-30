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
        'registry_url': docker_registry_url,
        'registry_project': docker_registry_project,
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
        helm_delete(release_name,  app.config['NAMESPACE'])
        print(e)
        return Response(
            f"We could not download your container",
            500
        )


def helm_install(payload, namespace):

    def _download_images_from_manifest(manifest):

        docker_containers = []
        manifest = json.dumps(manifest)
        print(manifest)
        regex = r'\"image\": \"([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)\"'
        matches = re.findall(regex, manifest)
        for match in matches:
            docker_containers.append({
                'docker_registry_url': match[0],
                'docker_registry_project': match[1],
                'docker_image': match[2],
                'docker_version': match[3]
            })
        print(docker_containers)
        for ds in docker_containers:
            try:
                resp = pull_docker_image(**ds)
                print(resp)
                print(resp.status)
                return Response(
                    f"We will try to download the image: {ds['docker_registry_url']}{ds['docker_registry_project']}({ds['docker_image']}:{ds['docker_version']}! Depending on your internet connection, this might take some time, please try again later!",
                    500
                )
            except requests.exceptions.ConnectionError as e:
                print(e)
                return Response(
                    f"You need to have a internet access to dktk-jip-registry.dkfz.de in order to install the chart! If the chart was installed once, you can deactivate again the internet access.",
                    500
                )
        return Response(
            f"We have trouble downloading the container. Please have a look into the logs of the kube-helm container to see, why the installation failed!",
            500
        )


    repoName, chartName = payload["name"].split('/')
    version = payload["version"]

    values = helm_show_values(repoName, chartName, payload["version"])
    default_sets =  {
        'global.registry_url': 'dktk-jip-registry.dkfz.de',
        'global.registry_project':  '/kaapana',
        'global.base_namespace': 'flow-jobs',
        'global.fast_data_dir': '/home/kaapana/',
        'global.slow_data_dir': '/home/kaapana/'
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
    helm_command = f'{os.environ["HELM_PATH"]} install -n {namespace} --version {version} {release_name} {helm_sets} {repoName}/{chartName} -o json --wait --timeout 0m8s'
    print('helm_command', helm_command)

    try:
        resp = subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True)
        resp = json.loads(resp)
        print('resp', resp)
        manifests = yaml.load_all(resp['manifest'], Loader=yaml.Loader)
        job_names = {}
        for manifest in manifests:
            if manifest['kind'] == 'Job':
                job_names.update({manifest['metadata']['name']: 'pending'})
        if job_names:
            t_end = time.time() + 6
            while time.time() < t_end:
                time.sleep(1)
                for job_name in job_names.keys():
                    print('job_name', job_name)
                    try:
                        job_pods = subprocess.check_output(f'kubectl -n flow get pods --selector=job-name=mitk-userflow -o custom-columns=NAME:.metadata.name,STATUS:.status.phase', stderr=subprocess.STDOUT, shell=True)
                        job_states = {}
                        for row in re.findall(r'(.*\n)', job_pods.decode("utf-8"))[1:]:
                            job_id, job_status = row.split()
                            print('pod and status', job_id, job_status)
                            job_states.update({job_id: job_status})
                        if (list(job_states.values()).count('Running') == len(job_states)) is True or \
                        (list(job_states.values()).count('Succeeded') == len(job_states)) is True:
                            job_names[job_name] = 'running_or_succeeded'
                    except subprocess.CalledProcessError as e:
                        helm_delete(release_name, namespace)
                        return Response(
                            f"We could not execute the job, please have look into the kubernetes logs of the job and the kube-helm pods",
                            500
                        )
                if (list(job_names.values()).count('running_or_succeeded') == len(job_names)) is True:
                    return Response(resp, 200)
            helm_delete(release_name, namespace)
            return _download_images_from_manifest(manifest)
        else:
            return Response(resp, 200)
    except subprocess.CalledProcessError as e:
        manifest = helm_get_manifest(release_name, namespace)
        helm_delete(release_name, namespace)
        return _download_images_from_manifest(manifest)


def helm_delete(release_name, namespace):
    try:
        print(f'deleting {release_name}')
        resp = subprocess.check_output(
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
            [os.environ["HELM_PATH"], "-n", namespace, "--filter", release_filter, "ls", "-o", "json"], stderr=subprocess.STDOUT
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