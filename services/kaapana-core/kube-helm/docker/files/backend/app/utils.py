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
from config import settings

charts_cached = None
charts_hashes = {}

refresh_delay = 30
smth_pending = False
update_running = False

last_refresh_timestamp = None
extensions_list_cached = []


def executue_shell_command(command, in_background=False, timeout=5):
    command = command.split(" ")
    command_result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", shell=in_background, timeout=timeout)
    stdout = command_result.stdout.strip()
    stderr = command_result.stderr.strip()
    return_code = command_result.returncode
    success = True if return_code == 0 else False

    return success, stdout, stderr


def sha256sum(filepath):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def helm_show_values(name, version):
    success, stdout, stderr = executue_shell_command(f'{settings.helm_path} show values {settings.helm_extensions_cache}/{name}-{version}.tgz')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        return {}


def helm_repo_index(repo_dir):
    helm_command = f'{settings.helm_path} repo index {repo_dir}'
    success, stdout, stderr = executue_shell_command(helm_command)


def helm_show_chart(name=None, version=None, package=None):
    helm_command = f'{settings.helm_path} show chart'

    if package is not None:
        helm_command = f'{helm_command} {package}'
    else:
        helm_command = f'{helm_command} {settings.helm_extensions_cache}/{name}-{version}.tgz'

    success, stdout, stderr = executue_shell_command(helm_command)

    if success:
        yaml_dict = list(yaml.load_all(stdout, yaml.FullLoader))[0]
        return yaml_dict
    else:
        return {}


def helm_get_manifest(release_name, helm_namespace=settings.helm_namespace):

    success, stdout, stderr = executue_shell_command(f'{settings.helm_path} -n {helm_namespace} get manifest {release_name}')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))
    else:
        return []


def helm_get_values(release_name, helm_namespace=settings.helm_namespace):
    success, stdout, stderr = executue_shell_command(f'{settings.helm_path} -n {helm_namespace} get values -o json {release_name}')
    if success and stdout != b'null\n':
        return json.loads(stdout)
    else:
        return dict()


def helm_status(release_name, helm_namespace=settings.helm_namespace):
    success, stdout, stderr = executue_shell_command(f'{settings.helm_path} -n {helm_namespace} status {release_name}')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        return dict()


def helm_prefetch_extension_docker(helm_namespace=settings.helm_namespace):
    # regex = r'image: ([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)'
    regex = r'image: (.*)\/([\w\-\.]+):([\w\-\.]+)'
    extensions = helm_search_repo(keywords_filter=['kaapanaapplication', 'kaapanaint', 'kaapanaworkflow'])
    installed_release_names = []
    dags = []
    image_dict = {}
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

        # if 'kaapanaexperimental' in chart["keywords"]:
        #     print(f'Skipping {chart_name}, since its experimental')
        #     continue
        if 'kaapanaworkflow' in chart["keywords"]:
            dags.append(payload)
        else:
            print(f'Prefetching {chart_name}')
            if helm_status(payload["name"]):
                print(f'Skipping {payload["name"]} since it is already installed')
                continue
            release, _, release_name = helm_install(payload, helm_command_addons='--dry-run', in_background=False)
            manifest = json.loads(release.decode("utf-8"))["manifest"]
            matches = re.findall(regex, manifest)
            if matches:
                for match in matches:
                    docker_registry_url = match[0]
                    docker_image = match[1]
                    docker_version = match[2]
                    image_dict.update({f'{docker_registry_url}/{docker_image}:{docker_version}': {
                        'docker_registry_url': docker_registry_url,
                        'docker_image': docker_image,
                        'docker_version': docker_version
                    }})

    for name, payload in image_dict.items():
        try:
            release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
            release, helm_command, release_name = pull_docker_image(release_name, **payload, in_background=False)
            installed_release_names.append(release_name)
        except subprocess.CalledProcessError as e:
            helm_delete(release_name=release_name, release_version=chart["version"])
            raise ValueError(e)

    for dag in dags:
        try:
            print(f'Prefetching {dag["name"]}')
            dag['sets'] = {
                'action': 'prefetch'
            }
            if helm_status(dag["name"]):
                print(f'Skipping {dag["name"]} since it is already installed')
                continue
            helm_comman_suffix = f'--wait --atomic --timeout=120m0s; sleep 10;{settings.helm_path} -n {helm_namespace} delete --no-hooks {dag["release_name"]}'
            release, helm_command, release_name = helm_install(dag, helm_comman_suffix=helm_comman_suffix, in_background=False)
            installed_release_names.append(release_name)
        except subprocess.CalledProcessError as e:
            helm_delete(release_name=dag['release_name'], release_version=chart["version"], helm_command_addons='--no-hooks')
            raise ValueError(e)

    return installed_release_names


def pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, timeout='120m0s', helm_namespace=settings.helm_namespace, in_background=True):
    print(f'Pulling {docker_registry_url}/{docker_image}:{docker_version}')

    try:
        helm_repo_index(settings.helm_helpers_cache)
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)

    with open(os.path.join(settings.helm_helpers_cache, 'index.yaml'), 'r') as stream:
        try:
            helper_charts = list(yaml.load_all(stdout, yaml.FullLoader))[0]
        except yaml.YAMLError as exc:
            print(exc)

    if "{default_platform_abbr}_{default_platform_version}" in docker_version:
        docker_version = docker_version.replace("{default_platform_abbr}_{default_platform_version}", f"{os.getenv('PLATFORM_ABBR')}_{os.getenv('PLATFORM_VERSION')}")
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

    helm_comman_suffix = f'--wait --atomic --timeout {timeout}; sleep 10;{settings.helm_path} -n {helm_namespace} delete {release_name}'
    return helm_install(payload, helm_comman_suffix=helm_comman_suffix, helm_cache_path=settings.helm_helpers_cache, in_background=in_background)


def helm_install(payload, helm_namespace=settings.helm_namespace, helm_command_addons='', helm_comman_suffix='', helm_delete_prefix='', in_background=True, helm_cache_path=None):
    global smth_pending, extensions_list_cached
    smth_pending = True

    helm_cache_path = helm_cache_path or settings.helm_extensions_cache

    name = payload["name"]
    version = payload["version"]

    release_values = helm_get_values(os.getenv("RELEASE_NAME"))

    default_sets = {}
    if 'global' in release_values:
        for k, v in release_values['global'].items():
            default_sets[f'global.{k}'] = v
    default_sets.pop('global.preinstall_extensions', None)
    default_sets.pop('global.kaapana_collections', None)

    print('Using default sets')
    print(json.dumps(default_sets, indent=4, sort_keys=True))

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
            return "Already installed!", "Nothing more to say", release_name

    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            value = value.replace(",", "\,").replace("'", '\'"\'').replace(" ", "")
            helm_sets = helm_sets + f" --set {key}='{value}'"

    helm_command = f'{helm_delete_prefix}{settings.helm_path} -n {helm_namespace} install {helm_command_addons} {release_name} {helm_sets} {helm_cache_path}/{name}-{version}.tgz -o json {helm_comman_suffix}'
    for item in extensions_list_cached:
        if item["releaseName"] == release_name and item["version"] == version:
            item["successful"] = 'pending'

    print('Executing')
    print(helm_command)
    success, stdout, stderr = executue_shell_command(helm_command, in_background=in_background)

    return stdout, helm_command, release_name


def helm_delete(release_name, helm_namespace=settings.helm_namespace, release_version=None, helm_command_addons=''):
    # release version only important for extensions charts!
    global smth_pending, extensions_list_cached
    smth_pending = True
    helm_command = f'{settings.helm_path} -n {helm_namespace} uninstall {helm_command_addons} {release_name}'
    success, stdout, stderr = executue_shell_command(helm_command, in_background=True)
    if release_version is not None:
        for item in extensions_list_cached:
            if item["releaseName"] == release_name and item["version"] == release_version:
                item["successful"] = 'pending'


def helm_ls(helm_namespace=settings.helm_namespace, release_filter=''):
    command = f'{settings.helm_path} -n {helm_namespace} --filter {release_filter} ls --deployed --pending --failed --uninstalling -o json'
    success, stdout, stderr = executue_shell_command(command=command, in_background=False)

    if success:
        return json.loads(stdout)
    else:
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

    # Todo might be replaced by json or yaml output in the future with the flag -o json!
    success, stdout, stderr = executue_shell_command(f"{settings.kubectl_path} -n {namespace} get pod -l={kind}-name={name}")
    # success, stdout, stderr = executue_shell_command(f"{settings.kubectl_path} -n {namespace} get pod -l={kind}-name={name} -o json")
    if success:
        # kube_info = json.loads(stdout)
        stdout = stdout.splitlines()[1:]
        for row in stdout:
            name, ready, status, restarts, age = re.split('\s\s+', row)
            states['name'].append(name)
            states['ready'].append(ready)
            states['status'].append(status)
            states['restarts'].append(restarts)
            states['age'].append(age)
    else:
        print(f'Could not get kube status of {name}')
        print(stderr)

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
    return success, extensions_list_cached

# Copied from kaapna_utils.py, maybe overhad...


def cure_invalid_name(name, regex, max_length=None):
    def _regex_match(regex, name):
        if re.fullmatch(regex, name) is None:
            invalid_characters = re.sub(regex, '', name)
            for c in invalid_characters:
                name = name.replace(c, '')
            print(f'Your name does not fullfill the regex {regex}, we adapt it to {name} to work with Kubernetes')
        return name
    name = _regex_match(regex, name)
    if max_length is not None and len(name) > max_length:
        name = name[:max_length]
        print(f'Your name is too long, only {max_length} character are allowed, we will cut it to {name} to work with Kubernetes')
    name = _regex_match(regex, name)
    return name


def execute_update_extensions():

    chart = {
        'name': 'update-collections-chart',
        'version': '0.1.0'
    }
    print(chart['name'], chart['version'])
    payload = {k: chart[k] for k in ('name', 'version')}

    install_error = False
    message = f"No kaapana_collections defined..."
    for idx, kube_helm_collection in enumerate(settings.kaapana_collections.split(';')[:-1]):
        release_name = cure_invalid_name("-".join(kube_helm_collection.split('/')[-1].split(':')), r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)
        payload.update({
            'release_name': release_name,
            'sets': {
                'kube_helm_collection': kube_helm_collection
            }
        })

        if not helm_status(release_name):
            try:
                print(f'Installing {release_name}')
                helm_install(
                    payload, helm_cache_path=settings.helm_collections_cache, in_background=False)
                message = f"Successfully updated the extensions"
            except subprocess.CalledProcessError as e:
                install_error = True
                helm_delete(release_name)
                print(e)
                message = f"We had troubles updating the extensions"
        else:
            try:
                print('helm deleting and reinstalling')
                helm_delete_prefix = f'{settings.helm_path} -n {settings.helm_namespace} uninstall {release_name} --wait --timeout 5m;'
                helm_install(payload, helm_delete_prefix=helm_delete_prefix, helm_command_addons="--wait",
                             helm_cache_path=settings.helm_collections_cache, in_background=False)
                message = f"Successfully updated the extensions"
            except subprocess.CalledProcessError as e:
                install_error = True
                helm_delete(release_name)
                print(e)
                message = f"We had troubles updating the extensions"

    return install_error, message
