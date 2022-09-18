import os
import glob
from os.path import basename
from typing import Tuple
import re
import json
import subprocess
import hashlib
import time

import yaml
import secrets
import json

from distutils.version import LooseVersion
from fastapi import Response
from fastapi.logger import logger

from config import settings
from helm_helper import execute_shell_command


CHART_STATUS_UNDEPLOYED = "un-deployed"
CHART_STATUS_DEPLOYED = "deployed"
CHART_STATUS_UNINSTALLING = "uninstalling"
KUBE_STATUS_RUNNING = "running"
KUBE_STATUS_COMPLETED = "completed"
KUBE_STATUS_PENDING = "pending"
KUBE_STATUS_UNKNOWN = "unknown"

charts_cached = None
charts_hashes = {}

refresh_delay = 30
smth_pending = False
update_running = False

last_refresh_timestamp = None
global_extensions_dict_cached = []


def sha256sum(filepath):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def helm_show_values(name, version):
    success, stdout = execute_shell_command(
        f'{settings.helm_path} show values {settings.helm_extensions_cache}/{name}-{version}.tgz')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        return {}


def helm_repo_index(repo_dir):
    helm_command = f'{settings.helm_path} repo index {repo_dir}'
    _, _ = execute_shell_command(helm_command)


def helm_show_chart(name=None, version=None, package=None):
    helm_command = f'{settings.helm_path} show chart'

    if package is not None:
        helm_command = f'{helm_command} {package}'
    else:
        helm_command = f'{helm_command} {settings.helm_extensions_cache}/{name}-{version}.tgz'

    success, stdout = execute_shell_command(helm_command)

    if success:
        yaml_dict = list(yaml.load_all(stdout, yaml.FullLoader))[0]
        return yaml_dict
    else:
        return {}


def helm_search_repo(keywords_filter):
    global charts_cached
    keywords_filter = set(keywords_filter)

    if check_modified() or charts_cached == None:
        logger.info("Charts modified -> generating new list.", flush=True)
        helm_packages = [f for f in glob.glob(
            os.path.join(settings.helm_extensions_cache, '*.tgz'))]
        charts_cached = {}
        for helm_package in helm_packages:
            chart = helm_show_chart(package=helm_package)
            if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                chart = add_extension_params(chart)
                charts_cached[f'{chart["name"]}-{chart["version"]}'] = chart

    return charts_cached


def get_kube_status(kind, name, namespace):
    states = None
    # Todo might be replaced by json or yaml output in the future with the flag -o json!
    success, stdout = execute_shell_command(
        f"{settings.kubectl_path} -n {namespace} get pod -l={kind}-name={name}")
    # success, stdout, stderr = execute_shell_command(f"{settings.kubectl_path} -n {namespace} get pod -l={kind}-name={name} -o json")
    if success:
        states = {
            "name": [],
            "ready": [],
            "status": [],
            "restarts": [],
            "age": []
        }
        # kube_info = json.loads(stdout)
        stdout = stdout.splitlines()[1:]
        for row in stdout:
            name, ready, status, restarts, age = re.split('\s\s+', row)
            states['name'].append(name)
            states['ready'].append(ready)
            states['status'].append(status.lower())
            states['restarts'].append(restarts)
            states['age'].append(age)
    else:
        logger.error(f'Could not get kube status of {name}')
        logger.error(stdout)

    return states


def helm_get_kube_objects(release_name, helm_namespace=settings.helm_namespace):

    success, stdout = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} get manifest {release_name}')

    kube_status = None
    ingress_paths = []
    concatenated_states = {
        "name": [],
        "ready": [],
        "status": [],
        "restarts": [],
        "age": []
    }
    if success:
        manifest_dict = list(yaml.load_all(stdout, yaml.FullLoader))
        deployment_ready = True

        for config in manifest_dict:
            if config is None:
                continue
            if config['kind'] == 'Ingress':
                ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
                ingress_paths.append(ingress_path)

            elif config['kind'] == 'Deployment' or config['kind'] == 'Job':
                if config['kind'] == 'Deployment':
                    obj_kube_status = get_kube_status(
                        'app', config['spec']['selector']['matchLabels']['app-name'], config['metadata']['namespace'])
                elif config['kind'] == 'Job':
                    obj_kube_status = get_kube_status(
                        'job', config['metadata']['name'], config['metadata']['namespace'])

                if obj_kube_status != None:
                    for key, value in obj_kube_status.items():
                        concatenated_states[key] = concatenated_states[key] + value
                        if key == "status" and value[0] != KUBE_STATUS_COMPLETED and value[0] != KUBE_STATUS_RUNNING:
                            deployment_ready = False
    else:
        deployment_ready = False

    return success, deployment_ready, ingress_paths, concatenated_states


def helm_get_values(release_name, helm_namespace=settings.helm_namespace):
    success, stdout = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} get values -o json {release_name}')
    if success and stdout != b'null\n':
        return json.loads(stdout)
    else:
        return dict()


def helm_status(release_name, helm_namespace=settings.helm_namespace):
    success, stdout = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} status {release_name}')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        logger.error(
            f"WARNING: Could not fetch helm status for: {release_name}")
        return []


def collect_helm_deployments(helm_namespace=settings.helm_namespace):
    success, stdout = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} ls --deployed --pending --failed --uninstalling --superseded -o json')
    if success:
        namespace_deployments = json.loads(stdout)
        deployed_charts_dict = {}
        for chart in namespace_deployments:
            if chart["chart"] not in deployed_charts_dict:
                deployed_charts_dict[chart["chart"]] = [chart]
            else:
                deployed_charts_dict[chart["chart"]].append(chart)

        return deployed_charts_dict

    else:
        return []


def helm_prefetch_extension_docker(helm_namespace=settings.helm_namespace):
    # regex = r'image: ([\w\-\.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\.]+)'
    regex = r'image: (.*)\/([\w\-\.]+):([\w\-\.]+)'
    extensions = helm_search_repo(
        keywords_filter=['kaapanaapplication', 'kaapanaint', 'kaapanaworkflow'])
    installed_release_names = []
    dags = []
    image_dict = {}
    for chart_name, chart in extensions.items():
        if os.path.isfile(f'{settings.helm_extensions_cache}/{chart_name}.tgz') is not True:
            logger.warning(f'{chart_name} not found')
            continue
        payload = {
            'name': chart["name"],
            'version': chart["version"],
            'keywords': chart["keywords"],
            'release_name': f'prefetch-{chart_name}'
        }

        if 'kaapanaworkflow' in chart["keywords"]:
            dags.append(payload)
        else:
            logger.info(f'Prefetching {chart_name}')
            if helm_status(payload["name"]):
                logger.info(
                    f'Skipping {payload["name"]} since it is already installed')
                continue
            success, stdout, helm_result_dict = helm_install(
                payload, helm_command_addons='--dry-run', shell=False)
            manifest = helm_result_dict["manifest"]
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
        release_name = f'pull-docker-chart-{secrets.token_hex(10)}'
        success, stdout, helm_result_dict = pull_docker_image(
            release_name, **payload, shell=False)
        if success:
            installed_release_names.append(release_name)
        else:
            helm_delete(release_name=release_name,
                        release_version=chart["version"])

    for dag in dags:
        logger.info(f'Prefetching {dag["name"]}')
        dag['sets'] = {
            'action': 'prefetch'
        }
        if helm_status(dag["name"]):
            logger.info(
                f'Skipping {dag["name"]} since it is already installed')
            continue
        helm_command_suffix = f'--wait --atomic --timeout=120m0s; sleep 10;{settings.helm_path} -n {helm_namespace} delete --no-hooks {dag["release_name"]}'
        success, stdout, helm_result_dict = helm_install(
            dag, helm_command_suffix=helm_command_suffix, shell=False)
        if success:
            installed_release_names.append(release_name)
        else:
            helm_delete(release_name=dag['release_name'],
                        release_version=chart["version"], helm_command_addons='--no-hooks')

    return installed_release_names


def pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, timeout='120m0s', helm_namespace=settings.helm_namespace, shell=True):
    # TODO: this function runs helm_install w/ shell=True, this is not safe and should not be used if it is not absolutely necessary
    logger.info(
        f'Pulling {docker_registry_url}/{docker_image}:{docker_version}')

    try:
        helm_repo_index(settings.helm_helpers_cache)
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)

    with open(os.path.join(settings.helm_helpers_cache, 'index.yaml'), 'r') as stream:
        try:
            helper_charts = list(yaml.load_all(stdout, yaml.FullLoader))[0]
        except yaml.YAMLError as exc:
            logger.error(exc)

    if "{default_platform_abbr}_{default_platform_version}" in docker_version:
        docker_version = docker_version.replace(
            "{default_platform_abbr}_{default_platform_version}", f"{os.getenv('PLATFORM_ABBR')}_{os.getenv('PLATFORM_VERSION')}")
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

    helm_command_suffix = f'--wait --atomic --timeout {timeout}; sleep 10;{settings.helm_path} -n {helm_namespace} delete {release_name}'
    success, stdout, helm_result_dict = helm_install(
        payload, helm_command_suffix=helm_command_suffix, helm_cache_path=settings.helm_helpers_cache, shell=shell)
    return success, helm_result_dict


def helm_install(
    payload,
    helm_namespace=settings.helm_namespace,
    helm_command_addons='',
    helm_command_suffix='',
    helm_delete_prefix='',
    shell=True,
    helm_cache_path=None
) -> Tuple[bool, str, str, str]:
    # TODO: must be shell=False as default
    """
        Returns success[bool], stdout[str], helm_command[str], release_name[str]
    """
    logger.debug("installing helm chart with payload {0}".format(payload))
    global smth_pending, global_extensions_dict_cached
    smth_pending = True

    helm_cache_path = helm_cache_path or settings.helm_extensions_cache

    name = payload["name"]
    version = payload["version"]

    # TODO
    # Instead of assuming there is only one platform running with a name like
    # '*-platform-chart', pass it as env var into kaapana-extensions-collection chart
    platform_name: str = helm_ls(release_filter="platform-chart")[0]["name"]
    release_values = helm_get_values(platform_name)

    default_sets = {}
    if 'global' in release_values:
        for k, v in release_values['global'].items():
            default_sets[f'global.{k}'] = v
    default_sets.pop('global.preinstall_extensions', None)
    default_sets.pop('global.kaapana_collections', None)

    if 'extension_params' in payload:
        for key, value in payload['extension_params'].items():
            if (";" not in key) and (";" not in value):
                default_sets.update({f'global.{key}': value})

    logger.debug('Using default sets')
    logger.debug(json.dumps(default_sets, indent=4, sort_keys=True))

    # get chart's values
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

    # check if the chart was installed before
    status = helm_status(release_name)
    if status:
        if 'kaapanamultiinstallable' in keywords:
            logger.info('Installing again since its kaapanamultiinstallable')
        elif helm_delete_prefix:
            logger.info('Deleting and then installing again!')
        else:
            logger.info("Chart is already installed")
            return False, "Chart is already installed", "", release_name
    else:
        logger.info("No previous installations were found")

    # creating --set variables from values
    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            value = value.replace(",", "\,").replace(
                "'", '\'"\'').replace(" ", "")
            helm_sets = helm_sets + f" --set {key}={value}"

    # make the whole command
    helm_command = f'{helm_delete_prefix}{os.environ["HELM_PATH"]} -n {helm_namespace} install {helm_command_addons} {release_name} {helm_sets} {helm_cache_path}/{name}-{version}.tgz -o json {helm_command_suffix}'
    for item in global_extensions_dict_cached:
        if item["releaseName"] == release_name and item["version"] == version:
            item["successful"] = 'pending'

    success, stdout = execute_shell_command(
        helm_command, shell)
    return success, stdout, helm_command, release_name


def helm_delete(release_name, helm_namespace=settings.helm_namespace, release_version=None, helm_command_addons=''):
    # release version only important for extensions charts!
    cached_extension = [
        x for x in global_extensions_dict_cached if x["releaseName"] == release_name]
    if len(cached_extension) == 1:
        release_name = cached_extension[0]["helm_info"]["name"]

    helm_command = f'{settings.helm_path} -n {helm_namespace} uninstall {helm_command_addons} {release_name}'
    success, stdout = execute_shell_command(
        helm_command, shell=False)
    if success and release_version is not None:
        for item in global_extensions_dict_cached:
            if item["releaseName"] == release_name and item["version"] == release_version:
                item["successful"] = 'pending'
    else:
        logger.warning(
            f"Something went wrong during the uninstallation of {release_name}:{release_version}")
        s = """"""
        for line in stdout.splitlines():
            s += line + "\n"
        s = s[:-1]
        logger.warning(s)


def helm_ls(helm_namespace=settings.helm_namespace, release_filter=''):
    """
        Returns all charts under namespace after applying the filter
    """
    # TODO: run subprocess via execute function and with shell=False
    try:
        resp = subprocess.check_output(
            f'{os.environ["HELM_PATH"]} -n {helm_namespace} --filter {release_filter} ls --deployed --pending --failed --uninstalling -o json', stderr=subprocess.STDOUT, shell=True)
        return json.loads(resp)
    except Exception as e:
        logger.error("Error when running helm ls: {0}".format(e))
        return []


def check_modified():
    global charts_hashes
    helm_packages = [f for f in glob.glob(
        os.path.join(settings.helm_extensions_cache, '*.tgz'))]
    modified = False
    new_charts_hashes = {}
    for helm_package in helm_packages:
        chart_hash = sha256sum(filepath=helm_package)
        if helm_package not in charts_hashes or chart_hash != charts_hashes[helm_package]:
            logger.warning(
                f"Chart {basename(helm_package)} has been modified!", flush=True)
            modified = True
        new_charts_hashes[helm_package] = chart_hash
    charts_hashes = new_charts_hashes
    return modified


def helm_search_repo(keywords_filter):
    global charts_cached
    keywords_filter = set(keywords_filter)

    if check_modified() or charts_cached == None:
        logger.info("Charts modified -> generating new list.", flush=True)
        helm_packages = [f for f in glob.glob(
            os.path.join(settings.helm_extensions_cache, '*.tgz'))]
        charts_cached = {}
        for helm_package in helm_packages:
            chart = helm_show_chart(package=helm_package)
            if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                charts_cached[f'{chart["name"]}-{chart["version"]}'] = chart

    return charts_cached


def get_extensions_list():
    global refresh_delay, global_extensions_dict_cached, last_refresh_timestamp, update_running

    if update_running or global_extensions_dict_cached == None or (last_refresh_timestamp != None and (time.time() - last_refresh_timestamp) < refresh_delay):
        return global_extensions_dict_cached

    logger.info("Generating new extension-list ...")

    global_extensions_dict = {}
    update_running = True
    available_extension_charts_tgz = helm_search_repo(
        keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
    deployed_extensions_dict = collect_helm_deployments()

    for extension_id, extension_dict in available_extension_charts_tgz.items():
        extension_name = extension_dict["name"]
        if extension_name not in global_extensions_dict:
            if 'kaapanaworkflow' in extension_dict['keywords']:
                extension_kind = 'dag'
            elif 'kaapanaapplication' in extension_dict['keywords']:
                extension_kind = 'application'
            else:
                logger.warning(
                    f"ISSUE: Unknown 'extension['kind']' - {extension_id}: {extension_dict['keywords']}")
                continue

            global_extensions_dict[extension_name] = {
                "releaseName": extension_name,
                "version": None,
                "versions": [],
                "installed": None,
                "ready": None,
                "links": None,
                "helm_status": None,
                "kube_status": None,
                "helm_info": None,
                "kube_info": None,
                "keywords": extension_dict['keywords'],
                "experimental": 'yes' if 'kaapanaexperimental' in extension_dict['keywords'] else 'no',
                "multiinstallable": 'yes' if 'kaapanamultiinstallable' in extension_dict['keywords'] else 'no',
                "kind": extension_kind
            }

        global_extensions_dict[extension_name]['version'] = extension_dict["version"]
        if extension_dict["version"] not in global_extensions_dict[extension_name]["versions"]:
            global_extensions_dict[extension_name]["versions"].append(
                extension_dict["version"])
            extension_versions = sorted(
                global_extensions_dict[extension_name]["versions"], key=LooseVersion, reverse=True)
            global_extensions_dict[extension_name]["latest_version"] = extension_versions[-1]

        if extension_id in deployed_extensions_dict:
            global_extensions_dict[extension_name]["installed"] = True
            global_extensions_dict[extension_name]["helm_status"] = deployed_extensions_dict[extension_id]["status"]
            global_extensions_dict[extension_name]["helm_info"] = deployed_extensions_dict[extension_id]
            if global_extensions_dict[extension_name]["helm_status"] == CHART_STATUS_DEPLOYED:
                success, deployment_ready, ingress_paths, concatenated_states = helm_get_kube_objects(
                    deployed_extensions_dict[extension_id]["name"])
                if success:
                    global_extensions_dict[extension_name]["kube_status"] = concatenated_states["status"]
                    global_extensions_dict[extension_name]["kube_info"] = concatenated_states
                    global_extensions_dict[extension_name]['links'] = ingress_paths
                    global_extensions_dict[extension_name]['ready'] = deployment_ready
                else:
                    logger.info(
                        f"Could not request kube-state of: {deployed_extensions_dict[extension_id]['name']}")
                    global_extensions_dict[extension_name]["kube_status"] = KUBE_STATUS_UNKNOWN
                    global_extensions_dict[extension_name]['links'] = []
                    global_extensions_dict[extension_name]['ready'] = False

            elif global_extensions_dict[extension_name]["helm_status"] == CHART_STATUS_UNINSTALLING:
                global_extensions_dict[extension_name]["kube_status"] = KUBE_STATUS_UNKNOWN
                global_extensions_dict[extension_name]['links'] = []
                global_extensions_dict[extension_name]['ready'] = False

        else:
            global_extensions_dict[extension_name]["installed"] = False
            global_extensions_dict[extension_name]['ready'] = False

        if global_extensions_dict[extension_name]["installed"]:
            if global_extensions_dict[extension_name]['ready']:
                global_extensions_dict[extension_name]['successful'] = "yes"
            else:
                global_extensions_dict[extension_name]['successful'] = "pending"
        else:
            global_extensions_dict[extension_name]['successful'] = "none"

        global_extensions_dict[extension_name]['installed'] = "yes" if global_extensions_dict[extension_name]['installed'] else "no"
        global_extensions_dict[extension_name]['helm_status'] = "" if global_extensions_dict[
            extension_name]['helm_status'] == None else global_extensions_dict[extension_name]['helm_status']
        global_extensions_dict[extension_name]['kube_status'] = "" if global_extensions_dict[
            extension_name]['kube_status'] == None else global_extensions_dict[extension_name]['kube_status']
        global_extensions_dict[extension_name]['version'] = global_extensions_dict[extension_name][
            'latest_version'] if global_extensions_dict[extension_name]['version'] == None else global_extensions_dict[extension_name]['version']
        global_extensions_dict[extension_name]['name'] = global_extensions_dict[extension_name]['releaseName']
        global_extensions_dict[extension_name]['helmStatus'] = global_extensions_dict[extension_name]['helm_status']
        global_extensions_dict[extension_name]['kubeStatus'] = global_extensions_dict[extension_name]['kube_status']

    last_refresh_timestamp = time.time()
    update_running = False
    result_list = []
    for key, value in global_extensions_dict.items():
        result_list.append(value)
    global_extensions_dict_cached = result_list

    return global_extensions_dict_cached


def cure_invalid_name(name, regex, max_length=None):
    def _regex_match(regex, name):
        if re.fullmatch(regex, name) is None:
            invalid_characters = re.sub(regex, '', name)
            for c in invalid_characters:
                name = name.replace(c, '')
            logger.warning(
                f'Your name does not fullfill the regex {regex}, we adapt it to {name} to work with Kubernetes')
        return name
    name = _regex_match(regex, name)
    if max_length is not None and len(name) > max_length:
        name = name[:max_length]
        logger.warning(
            f'Your name is too long, only {max_length} character are allowed, we will cut it to {name} to work with Kubernetes')
    name = _regex_match(regex, name)
    return name


def execute_update_extensions():
    chart = {
        'name': 'update-collections-chart',
        'version': '0.1.0'
    }
    logger.info(chart['name'], chart['version'])
    payload = {k: chart[k] for k in ('name', 'version')}

    install_error = False
    message = f"No kaapana_collections defined..."
    for idx, kube_helm_collection in enumerate(settings.kaapana_collections.split(';')[:-1]):
        release_name = cure_invalid_name("-".join(kube_helm_collection.split('/')[-1].split(
            ':')), r"[a-z0-9]([-a-z0-9]*[a-z0-9])?(\\.[a-z0-9]([-a-z0-9]*[a-z0-9])?)*", max_length=53)
        payload.update({
            'release_name': release_name,
            'sets': {
                'kube_helm_collection': kube_helm_collection
            }
        })

        if not helm_status(release_name):
            logger.info(f'Installing {release_name}')
            success, stdout, helm_result_dict = helm_install(
                payload, helm_cache_path=settings.helm_collections_cache, shell=False)
            if success:
                message = f"Successfully updated the extensions"
                logger.info(message)
            else:
                message = f"We had troubles updating the extensions"
                install_error = True
                helm_delete(release_name)
                logger.warning(message)
        else:
            logger.info('helm deleting and reinstalling')
            helm_delete_prefix = f'{settings.helm_path} -n {settings.helm_namespace} uninstall {release_name} --wait --timeout 5m;'
            success, stdout, helm_result_dict = helm_install(payload, helm_delete_prefix=helm_delete_prefix,
                                                             helm_command_addons="--wait", helm_cache_path=settings.helm_collections_cache, shell=False)
            if success:
                message = f"Successfully updated the extensions"
            else:
                install_error = True
                helm_delete(release_name)
                message = f"We had troubles updating the extensions"
                logger.error(message)

    return install_error, message


def add_extension_params(chart):
    """
    Add 'extension_params' to chart object, if a valid field exists in chart values.
    """
    vals = helm_show_values(chart["name"], chart["version"])
    if (vals is not None) and "extension_params" in vals:
        # TODO: validate the parameter field
        if ";" not in vals["extension_params"]:
            chart["extension_params"] = vals["extension_params"]
    return chart
