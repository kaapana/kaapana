import os
import glob
from os.path import basename
import yaml
import secrets
import re
import json
import subprocess
import json
import hashlib
import time
import copy
from flask import render_template, Response, request, jsonify
from distutils.version import LooseVersion
from app.repeat_timer import RepeatedTimer
from app import app

charts_cached = None
charts_hashes = {}

refresh_delay = 30
smth_pending = False
update_running = False

last_refresh_timestamp = None
extensions_list_cached = None


def sha256sum(filepath):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def helm_show_values(name, version):
    try:
        chart = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} show values {app.config["HELM_REPOSITORY_CACHE"]}/{name}-{version}.tgz', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print('Nothing found!')
        return {}
    return yaml.load(chart)


def helm_show_chart(name=None, version=None, package=None):
    helm_command = f'{os.environ["HELM_PATH"]} show chart'

    if package is not None:
        helm_command = f'{helm_command} {package}'
    else:
        helm_command = f'{helm_command} {app.config["HELM_REPOSITORY_CACHE"]}/{name}-{version}.tgz'
    try:
        chart = subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True)
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
    if values == b'null\n':
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
    extensions = helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaint', 'kaapanaworkflow'])

    dags = []
    for chart_name, chart in extensions.items():
        if os.path.isfile(f'{app.config["HELM_REPOSITORY_CACHE"]}/{chart_name}.tgz') is not True:
            print(f'{chart_name} not found')
            continue
        payload = {
            'name': chart["name"],
            'version': chart["version"],
            'keywords': chart["keywords"],
            'release_name': f'prefetch-{chart_name}'
        }

        if 'kaapanaexperimental' in chart["keywords"]:
            print(f'Skipping {chart_name}, since its experimental')
            continue
        elif 'kaapanaworkflow' in chart["keywords"]:
            dags.append(payload)
        else:
            print(f'Prefetching {chart_name}')
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
                print(f'Skipping {chart_name} due to {e.output.decode("utf-8")}')
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
        'name': f'pull-docker-chart',
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
    global smth_pending
    smth_pending = True

    name = payload["name"]
    version = payload["version"]


    default_sets = {
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

    http_proxy = os.getenv('PROXY', None)
    if http_proxy is not None and http_proxy != "":
        default_sets.update({
            'global.http_proxy': http_proxy,
            'global.https_proxy': http_proxy
        })

    values = helm_show_values(name, version)
    if 'keywords' not in payload:
        chart = helm_show_chart(name, version)
        if 'keywords' in chart:
            keywords = chart['keywords']
        else:
            keywords = []
    else:
        keywords = payload['keywords']

    if 'global' in values:
        for key, value in values['global'].items():
            if value != '':
                default_sets.update({f'global.{key}': value})

    if 'sets' not in payload:
        payload['sets'] = default_sets
    else:
        for key, value in default_sets.items():
            if key not in payload['sets'] or payload['sets'][key] == '':
                payload['sets'].update({key: value})

    if "release_name" in payload:
        release_name = payload["release_name"]
    elif 'kaapanamultiinstallable' in keywords:
        release_name = f'{name}-{secrets.token_hex(10)}'
    else:
        release_name = name

    status = helm_status(release_name, namespace)
    if status:
        if 'kaapanamultiinstallable' in keywords:
            print('Installing again since its kaapanamultiinstallable')
        else:
            return "already installed", 'no_helm_command'

    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            helm_sets = helm_sets + f" --set {key}='{value}'"

    helm_command = f'{os.environ["HELM_PATH"]} install {helm_command_addons} -n {namespace} {release_name} {helm_sets} {app.config["HELM_REPOSITORY_CACHE"]}/{name}-{version}.tgz -o json {helm_comman_suffix}'
    print('helm_command', helm_command)
    get_extensions_list()
    
    if in_background is False:
        return subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command
    else:
        return subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command


def helm_delete(release_name, namespace, helm_command_addons=''):
    global smth_pending
    smth_pending = True
    helm_command = f'{os.environ["HELM_PATH"]} delete {helm_command_addons} -n {namespace} {release_name}'
    subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)
    get_extensions_list()

def helm_ls(namespace, release_filter=''):
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {namespace} --filter {release_filter} ls --deployed --pending --failed --uninstalling -o json', stderr=subprocess.STDOUT, shell=True)
        return json.loads(resp)
    except subprocess.CalledProcessError as e:
        return []


def check_modified():
    global charts_hashes
    helm_packages = [f for f in glob.glob(os.path.join(app.config["HELM_REPOSITORY_CACHE"], '*.tgz'))]
    modified = False
    new_charts_hashes = {}
    for helm_package in helm_packages:
        chart_hash = sha256sum(filepath=helm_package)
        if helm_package not in charts_hashes or chart_hash != charts_hashes[helm_package]:
            print(f"Chart {basename(helm_package)} has been modified!", flush=True)
            modified = True
        new_charts_hashes[helm_package] = chart_hash
    charts_hashes = new_charts_hashes
    return modified


def helm_search_repo(keywords_filter):
    global charts_cached
    keywords_filter = set(keywords_filter)

    if check_modified():
        print("Charts modified -> generating new list.", flush=True)
        helm_packages = [f for f in glob.glob(os.path.join(app.config["HELM_REPOSITORY_CACHE"], '*.tgz'))]
        charts_cached = {}
        for helm_package in helm_packages:
            chart = helm_show_chart(package=helm_package)
            if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                charts_cached[f'{chart["name"]}-{chart["version"]}'] = chart
    return charts_cached


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
                concatenated_states[key] = concatenated_states[key] + value
        if config['kind'] == 'Job':
            kube_status = get_kube_status('job', config['metadata']['name'], config['metadata']['namespace'])
            for key, value in kube_status.items():
                concatenated_states[key] = concatenated_states[key] + value

    return concatenated_states, ingress_paths


def all_successful(status):
    successfull = ['Completed', 'Running', 'deployed']
    for i in status:
        if i not in successfull:
            return 'no'
    return 'yes'


def get_extensions_list():
    global refresh_delay, extensions_list_cached, last_refresh_timestamp, rt, smth_pending, update_running
    success = True
    try:
        if update_running or (not smth_pending and last_refresh_timestamp != None and extensions_list_cached != None and (time.time() - last_refresh_timestamp) < refresh_delay):
            # print("Using cached extension-list...", flush=True)
            pass
        else:
            # print("Generating new extension-list...", flush=True)
            smth_pending = False
            update_running = True
            available_charts = helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
            chart_version_dict = {}
            for _, chart in available_charts.items():
                if chart['name'] not in chart_version_dict:
                    chart_version_dict.update({chart['name']: []})
                chart_version_dict[chart['name']].append(chart['version'])

            extensions_list = []
            for name, versions in chart_version_dict.items():
                versions.sort(key=LooseVersion, reverse=True)
                latest_version = versions[0]
                extension = available_charts[f'{name}-{latest_version}']
                extension['versions'] = versions
                extension['version'] = latest_version
                extension['experimental'] = 'yes' if 'kaapanaexperimental' in extension['keywords'] else 'no'
                extension['multiinstallable'] = 'yes' if 'kaapanamultiinstallable' in extension['keywords'] else 'no'
                if 'kaapanaworkflow' in extension['keywords']:
                    extension['kind'] = 'dag'
                elif 'kaapanaapplication' in extension['keywords']:
                    extension['kind'] = 'application'
                else:
                    continue
                extension['releaseName'] = extension["name"]
                extension['helmStatus'] = ''
                extension['kubeStatus'] = ''
                extension['successful'] = 'none'

                status = helm_status(extension["name"], app.config['NAMESPACE'])
                if 'kaapanamultiinstallable' in extension['keywords'] or not status:
                    extension['installed'] = 'no'
                    extensions_list.append(extension)
                for release in helm_ls(app.config['NAMESPACE'], extension["name"]):
                    for version in extension["versions"]:
                        if release['chart'] == f'{extension["name"]}-{version}':
                            manifest = helm_get_manifest(release['name'], app.config['NAMESPACE'])
                            kube_status, ingress_paths = get_manifest_infos(manifest)

                            running_extension = copy.deepcopy(extension)
                            running_extension['releaseName'] = release['name']
                            running_extension['successful'] = all_successful(set(kube_status['status'] + [release['status']]))
                            running_extension['installed'] = 'yes'
                            running_extension['links'] = ingress_paths
                            running_extension['helmStatus'] = release['status'].capitalize()
                            running_extension['kubeStatus'] = ", ".join(kube_status['status'])
                            running_extension['version'] = version

                            if running_extension['successful'] != "yes":
                                print(f"Chart {release['name']} not ready: {running_extension['successful']} -> pending...", flush=True)
                                smth_pending = True
                            extensions_list.append(running_extension)

            last_refresh_timestamp = time.time()
            update_running = False
            extensions_list_cached = extensions_list

    except subprocess.CalledProcessError as e:
        success = False

    return success, extensions_list_cached


if charts_cached == None:
    helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

rt = RepeatedTimer(5, get_extensions_list)
