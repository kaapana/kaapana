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
from fastapi import Response
from distutils.version import LooseVersion
from app.repeat_timer import RepeatedTimer
from .config import settings

charts_cached = None
charts_hashes = {}

refresh_delay = 30
smth_pending = False
update_running = False

last_refresh_timestamp = None
extensions_list_cached = []


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
            f'{os.environ["HELM_PATH"]} show values {settings.helm_extensions_cache}/{name}-{version}.tgz', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print('Nothing found!')
        return {}
    return yaml.load(chart)


def helm_repo_index(repo_dir):
    helm_command = f'{os.environ["HELM_PATH"]} repo index {repo_dir}'
    subprocess.check_output(
        helm_command, stderr=subprocess.STDOUT, shell=True)


def helm_show_chart(name=None, version=None, package=None):
    helm_command = f'{os.environ["HELM_PATH"]} show chart'

    if package is not None:
        helm_command = f'{helm_command} {package}'
    else:
        helm_command = f'{helm_command} {settings.helm_extensions_cache}/{name}-{version}.tgz'
    try:
        chart = subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        print('Nothing online, nothing local!')
        return {}
    return yaml.load(chart)


def helm_get_manifest(release_name, helm_namespace=settings.helm_namespace):
    try:
        manifest = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {helm_namespace} get manifest {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return []
    return list(yaml.load_all(manifest))


def helm_get_values(release_name, helm_namespace=settings.helm_namespace):
    try:
        values = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {helm_namespace} get values -o json {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return dict()
    if values == b'null\n':
        return dict()
    return json.loads(values)


def helm_status(release_name, helm_namespace=settings.helm_namespace):
    try:
        status = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {helm_namespace} status {release_name}', stderr=subprocess.STDOUT, shell=True)
    except subprocess.CalledProcessError as e:
        return dict()
    return yaml.load(status)


def helm_prefetch_extension_docker(helm_namespace=settings.helm_namespace):
    # regex = r'image: ([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)'
    regex = r'image: (.*)\/([\w\-\.]+):([\w\-\.]+)'
    extensions = helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaint', 'kaapanaworkflow'])
    dags = []
    for chart_name, chart in extensions.items():
        if os.path.isfile(f'{settings.helm_extensions_cache}/{chart_name}.tgz') is not True:
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
                release, _ = helm_install(payload, helm_command_addons='--dry-run', in_background=False)
                manifest = json.loads(release.decode("utf-8"))["manifest"]
                matches = re.findall(regex, manifest)
                if matches:
                    for match in matches:
                        docker_registry_url = match[0]
                        docker_image = match[1]
                        docker_version = match[2]
                        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
                        try:
                            pull_docker_image(release_name, docker_image, docker_version, docker_registry_url)
                        except subprocess.CalledProcessError as e:
                            helm_delete(release_name=release_name, release_version=chart["version"])
                            print(e)
            except subprocess.CalledProcessError as e:
                print(f'Skipping {chart_name} due to {e.output.decode("utf-8")}')
    for dag in dags:
        try:
            print(f'Prefetching {dag["name"]}')
            dag['sets'] = {
                'action': 'prefetch'
            }
            helm_comman_suffix = f'--wait --atomic --timeout=120m0s; sleep 10;{os.environ["HELM_PATH"]} -n {helm_namespace} delete --no-hooks {dag["release_name"]}'
            helm_install(dag, helm_comman_suffix=helm_comman_suffix)
        except subprocess.CalledProcessError as e:
            print(f'Skipping {dag["name"]} due to {e.output.decode("utf-8")}')
            helm_delete(release_name=dag['release_name'], release_version=chart["version"], helm_command_addons='--no-hooks')


def pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, timeout='120m0s', helm_namespace=settings.helm_namespace):
    print(f'Pulling {docker_registry_url}/{docker_image}:{docker_version}')

    try:
        helm_repo_index(settings.helm_helpers_cache)
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)

    with open(os.path.join(settings.helm_helpers_cache, 'index.yaml'), 'r') as stream:
        try:
            helper_charts = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    payload = {
        'name': 'pull-docker-chart',
        'version': helper_charts['entries']['pull-docker-chart'][0]['version'],
        'sets': {
            'registry_url': docker_registry_url or os.getenv('REGISTRY_URL'),
            'image': docker_image,
            'version': docker_version
        },
        'release_name': release_name
    }

    helm_comman_suffix = f'--wait --atomic --timeout {timeout}; sleep 10;{os.environ["HELM_PATH"]} -n {helm_namespace} delete {release_name}'
    helm_install(payload, helm_comman_suffix=helm_comman_suffix, helm_cache_path=settings.helm_helpers_cache)


def helm_install(payload, helm_namespace=settings.helm_namespace, helm_command_addons='', helm_comman_suffix='', helm_delete_prefix='', in_background=True, helm_cache_path=None):
    global smth_pending, extensions_list_cached
    smth_pending = True

    helm_cache_path = helm_cache_path or settings.helm_extensions_cache

    name = payload["name"]
    version = payload["version"]

    # default_sets = {
    #     #'global.registry_url': os.getenv('REGISTRY_URL'),
    #     'global.base_namespace': os.getenv('BASE_NAMESPACE'),
    #     'global.flow_namespace': os.getenv('FLOW_NAMESPACE'),
    #     'global.flow_jobs_namespace': os.getenv('FLOW_JOBS_NAMESPACE'),
    #     #'global.fast_data_dir': os.getenv('FAST_DATA_DIR'),
    #     #'global.slow_data_dir': os.getenv('SLOW_DATA_DIR'),
    #     #'global.pull_policy_pods': os.getenv('PULL_POLICY_PODS'),
    #     #'global.pull_policy_jobs': os.getenv('PULL_POLICY_JOBS'),
    #     #'global.offline_mode': os.environ.get('OFFLINE_MODE', 'true'),
    #     'global.credentials_minio_username': os.getenv('MINIO_ACCESS_KEY'),
    #     'global.credentials_minio_password': os.getenv('MINIO_SECRET_KEY'),
    #     #'global.instance_name': os.getenv('INSTANCE_NAME'),
    #     #'global.hostname': os.getenv('HOSTNAME'),
    #     #'global.http_proxy': os.getenv('PROXY', ''),
    #     #'global.https_proxy': os.getenv('PROXY', ''),
    #     #'global.https_port': os.getenv('HTTPS_PORT', '443')
    # }

    default_sets = {
        'global.registry_url': os.getenv('REGISTRY_URL'),
        'global.platform_abbr': os.getenv('PLATFORM_ABBR'),
        'global.version': os.getenv('PLATFORM_VERSION'),
        'global.base_namespace': os.getenv('BASE_NAMESPACE'),
        'global.flow_namespace': os.getenv('FLOW_NAMESPACE'),
        'global.flow_jobs_namespace': os.getenv('FLOW_JOBS_NAMESPACE'),
        'global.fast_data_dir': os.getenv('FAST_DATA_DIR'),
        'global.slow_data_dir': os.getenv('SLOW_DATA_DIR'),
        'global.pull_policy_pods': os.getenv('PULL_POLICY_PODS'),
        'global.pull_policy_jobs': os.getenv('PULL_POLICY_JOBS'),
        'global.offline_mode': os.environ.get('OFFLINE_MODE', 'true'),
        'global.credentials_minio_username': os.getenv('MINIO_ACCESS_KEY'),
        'global.credentials_minio_password': os.getenv('MINIO_SECRET_KEY'),
        'global.instance_name': os.getenv('INSTANCE_NAME'),
        'global.hostname': os.getenv('HOSTNAME'),
        'global.http_proxy': os.getenv('PROXY', ''),
        'global.https_proxy': os.getenv('PROXY', ''),
        'global.https_port': os.getenv('HTTPS_PORT', '443')
    }

    # http_proxy = os.getenv('PROXY', None)
    # if http_proxy is not None and http_proxy != "":
    #     default_sets.update({
    #         'global.http_proxy': http_proxy,
    #         'global.https_proxy': http_proxy
    #     })

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

    status = helm_status(release_name)
    if status:
        if 'kaapanamultiinstallable' in keywords:
            print('Installing again since its kaapanamultiinstallable')
        elif helm_delete_prefix:
            print('Deleting and then installing again!')
        else:
            return "already installed", 'no_helm_command'

    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            helm_sets = helm_sets + f" --set {key}='{value}'"

    helm_command = f'{helm_delete_prefix}{os.environ["HELM_PATH"]} -n {helm_namespace} install {helm_command_addons} {release_name} {helm_sets} {helm_cache_path}/{name}-{version}.tgz -o json {helm_comman_suffix}'
    for item in extensions_list_cached:
        if item["releaseName"] == release_name and item["version"] == version:
            item["successful"] = 'pending'

    if in_background is False:
        return subprocess.check_output(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command
    else:
        return subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True), helm_command


def helm_delete(release_name, helm_namespace=settings.helm_namespace, release_version=None, helm_command_addons=''):
    # release version only important for extensions charts!
    global smth_pending, extensions_list_cached
    smth_pending = True
    helm_command = f'{os.environ["HELM_PATH"]} -n {helm_namespace} uninstall {helm_command_addons} {release_name}'
    subprocess.Popen(helm_command, stderr=subprocess.STDOUT, shell=True)
    if release_version is not None:
        for item in extensions_list_cached:
            if item["releaseName"] == release_name and item["version"] == release_version:
                item["successful"] = 'pending'


def helm_ls(helm_namespace=settings.helm_namespace, release_filter=''):
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {helm_namespace} --filter {release_filter} ls --deployed --pending --failed --uninstalling -o json', stderr=subprocess.STDOUT, shell=True)
        return json.loads(resp)
    except subprocess.CalledProcessError as e:
        return []


def check_modified():
    global charts_hashes
    helm_packages = [f for f in glob.glob(os.path.join(settings.helm_extensions_cache, '*.tgz'))]
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

    if check_modified() or charts_cached == None:
        print("Charts modified -> generating new list.", flush=True)
        helm_packages = [f for f in glob.glob(os.path.join(settings.helm_extensions_cache, '*.tgz'))]
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
        # Todo might be replaced by json or yaml output in the future with the flag -o json!
        resp = subprocess.check_output(
            f'kubectl -n {namespace} get pod -l={kind}-name={name}',
            stderr=subprocess.STDOUT,
            shell=True
        )
        for row in re.findall(r'(.*\n)', resp.decode("utf-8"))[1:]:           
            name, ready, status, restarts, age = re.split('\s\s+', row)
            states['name'].append(name)
            states['ready'].append(ready)
            states['status'].append(status)
            states['restarts'].append(restarts)
            states['age'].append(age)
    except subprocess.CalledProcessError as e:
        print(f'Could not get kube status of {name}')
        print(e)
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
        if config is None:
            continue
        ingress_path = ''
        if config['kind'] == 'Ingress':
            ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
            print('ingress_path', ingress_path)
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
            return "pending"
    
    return "yes"


def get_extensions_list():
    global refresh_delay, extensions_list_cached, last_refresh_timestamp, rt, smth_pending, update_running
    success = True
    extensions_list = []
    try:
        if update_running or (not smth_pending and last_refresh_timestamp != None and extensions_list_cached and (time.time() - last_refresh_timestamp) < refresh_delay):
            print("Using cached extension-list...", flush=True)
            pass
        else:
            print("Generating new extension-list...", flush=True)
            smth_pending = False
            update_running = True
            # replace with index yaml
            available_charts = helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
            chart_version_dict = {}
            for _, chart in available_charts.items():
                if chart['name'] not in chart_version_dict:
                    chart_version_dict.update({chart['name']: []})
                chart_version_dict[chart['name']].append(chart['version'])

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
                # replace with helm ls outside the loop see also next
                # add one central kubectl get pods -A from which manifest will look up its values

                status = helm_status(extension["name"])
                if 'kaapanamultiinstallable' in extension['keywords'] or not status:
                    extension['installed'] = 'no'
                    extensions_list.append(extension)
                for release in helm_ls(release_filter=extension["name"]):
                    for version in extension["versions"]:
                        if release['chart'] == f'{extension["name"]}-{version}':
                            manifest = helm_get_manifest(release['name'])
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
    print('success', success)
    return success, extensions_list_cached


if charts_cached == None:
    helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])

rt = RepeatedTimer(5, get_extensions_list)
