import os
from os.path import basename
import glob
import re
import json
import subprocess
import hashlib

import yaml
import secrets
import json

from typing import Tuple
from fastapi import Response
from fastapi.logger import logger

from config import settings
import schemas
import helm_helper

CHART_STATUS_UNDEPLOYED = "un-deployed"
CHART_STATUS_DEPLOYED = "deployed"
CHART_STATUS_UNINSTALLING = "uninstalling"
KUBE_STATUS_RUNNING = "running"
KUBE_STATUS_COMPLETED = "completed"
KUBE_STATUS_PENDING = "pending"
KUBE_STATUS_UNKNOWN = "unknown"

charts_cached = None
charts_hashes = {}


def all_successful(status):
    successful = ['completed', 'running', 'deployed']
    for i in status:
        if type(i) is not str or i.lower() not in successful:
            return "pending"

    return "yes"


def sha256sum(filepath):
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def helm_search_repo(keywords_filter):
    logger.debug("in function: helm_search_repo, with filter {0}".format(keywords_filter))
    global charts_cached
    keywords_filter = set(keywords_filter)

    if check_modified() or charts_cached == None:
        logger.info("Charts modified -> generating new list.")
        helm_packages = [f for f in glob.glob(
            os.path.join(settings.helm_extensions_cache, '*.tgz'))]
        charts_cached = {}
        for helm_package in helm_packages:
            chart = helm_helper.helm_show_chart(package=helm_package)
            if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                chart = helm_helper.add_extension_params(chart)
                charts_cached[f'{chart["name"]}-{chart["version"]}'] = chart

    return charts_cached


def helm_get_values(release_name, helm_namespace=settings.helm_namespace):
    logger.debug(f"in function: helm_get_values {release_name=}, {helm_namespace=}")
    success, stdout = helm_helper.execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} get values --all -o json {release_name}')
    if success and stdout != b'null\n':
        return json.loads(stdout)
    else:
        return dict()


def helm_status(release_name, helm_namespace=settings.helm_namespace):
    logger.debug("in function: helm_status")
    success, stdout = helm_helper.execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} status {release_name}')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        logger.error(
            f"WARNING: Could not fetch helm status for: {release_name}")
        return []


def collect_helm_deployments(helm_namespace=settings.helm_namespace):
    success, stdout = helm_helper.execute_shell_command(
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
    logger.debug("in function: helm_prefetch_extension_docker")
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
            success, stdout, helm_result_dict, _, _ = helm_install(
                payload, helm_command_addons='--dry-run', shell=True)
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
            release_name, blocking=True, **payload)
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
        helm_command_suffix = f'--wait --atomic --timeout=120m0s; sleep 10; {settings.helm_path} -n {helm_namespace} delete --no-hooks {dag["release_name"]}'
        success, stdout, helm_result_dict, release_name, _ = helm_install(
            dag, helm_command_suffix=helm_command_suffix, shell=True)
        installed_release_names.append(release_name)

    return installed_release_names


def pull_docker_image(release_name, docker_image, docker_version, docker_registry_url, timeout='120m0s', helm_namespace=settings.helm_namespace, shell=True,  blocking=False):
    logger.info(f'Pulling {docker_registry_url}/{docker_image}:{docker_version} , shell={shell}')

    try:
        helm_helper.helm_repo_index(settings.helm_helpers_cache)
    except subprocess.CalledProcessError as e:
        return Response(f"Could not create index.yaml!", 500)

    with open(os.path.join(settings.helm_helpers_cache, 'index.yaml'), 'r') as stream:
        try:
            helper_charts = list(yaml.load_all(stream, yaml.FullLoader))[0]
        except yaml.YAMLError as exc:
            logger.error(exc)

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

    helm_command_suffix = f'--wait --atomic --timeout {timeout}; sleep 10; {settings.helm_path} -n {helm_namespace} delete {release_name}'
    success, stdout, helm_result_dict, _, _ = helm_install(
        payload,
        helm_command_suffix=helm_command_suffix,
        helm_cache_path=settings.helm_helpers_cache,
        shell=shell,
        update_state=False,
        blocking=blocking
    )

    return success, helm_result_dict


def helm_install(
    payload,
    helm_namespace=settings.helm_namespace,
    helm_command_addons='',
    helm_command_suffix='',
    helm_delete_prefix='',
    shell=True,
    helm_cache_path=None,
    update_state=True,
    blocking=True,
    platforms=False,
    execute_cmd=True
) -> Tuple[bool, str, dict, str]:
    # TODO: must be shell=False as default
    """

    Args:
        payload (_type_): 
        helm_namespace (_type_, optional): . Defaults to settings.helm_namespace.
        helm_command_addons (str, optional): . Defaults to ''.
        helm_command_suffix (str, optional): . Defaults to ''.
        helm_delete_prefix (str, optional): . Defaults to ''.
        shell (bool, optional): Run command process with or without shell. Defaults to True.
        helm_cache_path (_type_, optional): _description_. Defaults to None.
        update_state (bool, optional): Whether to update global_extension_states. Defaults to True.
        blocking (bool, optional): Run helm install command in a blocking or non-blocking way. Defaults to True.

    Returns:
        Tuple[bool, str, dict, str, str]: success, stdout, helm_result_dict, release_name, helm_command
    """
    logger.debug("in function: helm_install with payload {0}, shell {1}".format(payload, shell))

    helm_cache_path = helm_cache_path or settings.helm_extensions_cache
    if platforms:
        assert settings.helm_platforms_cache is not None, f"HELM_PLATFORMS_CACHE is not defined"
        helm_cache_path = settings.helm_platforms_cache

    name = payload["name"]
    version = payload["version"]

    release_values = helm_get_values(settings.release_name)

    default_sets = {}
    if 'global' in release_values:
        for k, v in release_values['global'].items():
            default_sets[f'global.{k}'] = v
    default_sets.pop('global.preinstall_extensions', None)
    default_sets.pop('global.kaapana_collections', None)

    if 'extension_params' in payload:
        logger.debug(f"found extension_params in payload {payload['extension_params']}")
        for key, value in payload['extension_params'].items():
            if (";" not in key) and (";" not in str(value)):
                default_sets.update({f'global.{key}': value})

    logger.debug('Using default sets')
    logger.debug(json.dumps(default_sets, indent=4, sort_keys=True))

    # get chart's values
    values = helm_helper.helm_show_values(name, version, platforms)
    if 'keywords' not in payload:
        chart = helm_helper.helm_show_chart(name, version, platforms)
        if 'keywords' in chart:
            keywords = chart['keywords']
        else:
            keywords = []
    else:
        keywords = payload['keywords']

    if 'global' in values:
        for key, value in values['global'].items():
            if isinstance(value, str) and value != '':
                default_sets.update({f'global.{key}': value})
            elif isinstance(value, list) and value:
                for idx, sub_dict in enumerate(value):
                    for k, v in sub_dict.items():
                        default_sets[f'global.{key}[{idx}].{k}']  = v

    if 'kaapanamultiinstallable' in keywords:
        multi_installable_uuid = secrets.token_hex(5)
        default_sets['global.uuid'] = multi_installable_uuid
        
    if 'sets' not in payload:
        payload['sets'] = default_sets
    else:
        for key, value in default_sets.items():
            if key not in payload['sets'] or payload['sets'][key] == '':
                payload['sets'].update({key: value})

    if "release_name" in payload:
        release_name = payload["release_name"]
    elif 'kaapanamultiinstallable' in keywords:
        release_name = f'{name}-{multi_installable_uuid}'
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
            return False, "Chart is already installed", "", release_name, ""
    else:
        logger.info("No previous installations were found")

    if not platforms and "global.helm_namespace" in payload["sets"]:
        helm_namespace = payload["sets"]["global.helm_namespace"]

    if platforms:
        # current workaround for avoiding the namespace conflict
        helm_namespace = "default"
        helm_command_addons = ""
        # for preinstall, set correct helm_namespace for charts
        if "extension_params" in values and "helm_namespace" in values["extension_params"]:
            eparams = values["extension_params"]
            payload["sets"]["global.helm_namespace"] = eparams["helm_namespace"]["default"]

        # for preinstall, change path folder to extensions if doesn't exist
        curr_fpath = f"{helm_cache_path}/{name}-{version}.tgz"
        if not os.path.exists(curr_fpath) and helm_cache_path == settings.helm_platforms_cache:
            helm_cache_path = settings.helm_extensions_cache

    # creating --set variables from values
    helm_sets = ''
    if "sets" in payload:
        for key, value in payload["sets"].items():
            if type(value) == str:
                value = str(value).replace(",", "\,").replace("'", '\'"\'').replace(" ", "")
                helm_sets = helm_sets + f" --set-string {key}='{value}'"
            else:
                helm_sets = helm_sets + f" --set {key}='{value}'"


    # make the whole command
    helm_command = f'{settings.helm_path} -n {helm_namespace} install {helm_command_addons} {release_name} {helm_sets} {helm_cache_path}/{name}-{version}.tgz -o json {helm_command_suffix}'

    if not execute_cmd:
        return False, "", {}, release_name, helm_command

    skip_check = False
    if helm_command_suffix != "":
        skip_check = True
    if helm_delete_prefix != "":
        success, stdout = helm_helper.execute_shell_command(helm_delete_prefix, shell=shell, blocking=blocking, skip_check=skip_check)
        if not success:
            logger.error(f"helm delete prefix failed: cmd={helm_delete_prefix} success={success} stdout={stdout}")
    timeout=5
    if platforms:
        timeout = 15
    success, stdout = helm_helper.execute_shell_command(helm_command, shell=shell, blocking=blocking, timeout=timeout)

    helm_result_dict = {}
    if blocking and success:
        for item in helm_helper.global_extensions_dict_cached:
            if item["releaseName"] == release_name and item["version"] == version:
                item["successful"] = KUBE_STATUS_PENDING
        helm_result_dict = json.loads(stdout)

    if success and update_state and version is not None:
        helm_helper.update_extension_state(
            schemas.ExtensionStateUpdate.construct(
                extension_name=release_name,
                extension_version=version,
                state=schemas.ExtensionStateType.INSTALLED,
                multiinstallable=(True if "kaapanamultiinstallable" in keywords else False)
            )
        )

    return success, stdout, helm_result_dict, release_name, helm_command


def helm_delete(
    release_name,
    helm_namespace=settings.helm_namespace,
    release_version=None,
    helm_command_addons='',
    update_state=True,
    multiinstallable=False,
    platforms=False
):
    # release version only important for extensions charts
    cached_extension = []
    if platforms:
        cached_extension = [
            x for x in helm_helper.global_platforms_list if x["releaseName"] == release_name]
    else:
        cached_extension = [
            x for x in helm_helper.global_extensions_dict_cached if x["releaseName"] == release_name]

    if len(cached_extension) == 1:
        ext = cached_extension[0]
        versions = ext.available_versions
        dep = list(versions.items())[0][1]
        if release_version is not None:
            dep = versions[release_version]

        release_name = dep.deployments[0].helm_info.name

        if ext.multiinstallable == "yes":
            release_name = dep.deployments[0].helm_info.name

    # delete version
    helm_command = f'{settings.helm_path} -n {helm_namespace} uninstall {helm_command_addons} {release_name}'
    success, stdout = helm_helper.execute_shell_command(helm_command, shell=True, blocking=False)
    if success:
        if release_version is not None:
            for item in helm_helper.global_extensions_dict_cached:
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

        # handle 'Hook post-delete <hook-yaml-path> failed, jobs.batch <remove-job> already exists scenarios'
        if "post-delete" in stdout:
            logger.info(f"detected post-delete error during helm uninstall stdout: {stdout}")
            cmd = f'{settings.helm_path} -n {helm_namespace} ls --deployed --pending -o json'
            helm_success, helm_stdout = helm_helper.execute_shell_command(cmd)
            if not helm_success:
                err = f"Failed to run {cmd}, uninstall error: {stdout}"
                logger.error(err)
                return False, err

            json_out = json.loads(helm_stdout)
            logger.debug(f"json output for helm ls {json_out=}")

            # check whether the release still exists in deployed charts
            found = False
            for release in json_out:
                if release["name"] == release_name:
                    logger.debug("found the release in helm ls results, release: {0}".format(release))
                    found = True
                    break
            if not found:
                logger.debug(f"{release_name} is not found in deployed helm charts")
                success = True

    if success and update_state and release_version is not None:
        helm_helper.update_extension_state(
            schemas.ExtensionStateUpdate.construct(
                extension_name=release_name,
                extension_version=release_version,
                state=schemas.ExtensionStateType.NOT_INSTALLED,
                multiinstallable=multiinstallable
            )
        )

    return success, stdout


def helm_ls(helm_namespace=settings.helm_namespace, release_filter=''):
    """
        Returns all charts under namespace (in all states) after applying the filter
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
                f"Chart {basename(helm_package)} has been modified!")
            modified = True
        new_charts_hashes[helm_package] = chart_hash
    charts_hashes = new_charts_hashes
    return modified


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
    """

    Returns:
        install_error (bool): Whether there was an error during the installation
        message (str): Describes the state of execution
    """
    logger.debug(f"in function: execute_update_extensions")
    chart = {
        'name': 'update-collections-chart',
        'version': '0.0.0'
    }
    logger.info("chart info for update extensions {0}, {1}".format(chart['name'], chart['version']))
    payload = {k: chart[k] for k in ('name', 'version')}

    install_error = False
    message = f"No kaapana_collections defined..."
    logger.info("split kaapana collections {0}".format(settings.kaapana_collections.split(';')[:-1]))
    for idx, kube_helm_collection in enumerate(settings.kaapana_collections.split(';')[:-1]):
        logger.debug("kube_helm_collection {0}".format(kube_helm_collection))
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
            success, _, _, _, _ = helm_install(
                payload, helm_cache_path=settings.helm_collections_cache, shell=True, update_state=False)
            if success:
                message = f"Successfully updated the extensions"
                logger.info(message)
            else:
                message = f"We had troubles updating the extensions"
                install_error = True
                helm_delete(release_name, update_state=False)
                logger.warning(message)
        else:
            logger.info('helm deleting and reinstalling')
            helm_delete_prefix = f'{settings.helm_path} -n {settings.helm_namespace} uninstall {release_name} --wait --timeout 5m'
            success, _, _, _, _ = helm_install(
                payload, helm_delete_prefix=helm_delete_prefix, helm_command_addons="--wait",
                helm_cache_path=settings.helm_collections_cache, shell=True, update_state=False)
            if success:
                message = f"Successfully updated the extensions"
                logger.info(message)
            else:
                install_error = True
                helm_delete(release_name, update_state=False)
                message = f"We had troubles updating the extensions"
                logger.error(message)

    return install_error, message
