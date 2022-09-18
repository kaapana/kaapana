import os
import glob
from os.path import basename
import yaml
import re
import json
import subprocess
import json
import hashlib
import time
from distutils.version import LooseVersion
from config import settings
from fastapi.logger import logger

CHART_STATUS_UNDEPLOYED = "un-deployed"
CHART_STATUS_DEPLOYED = "deployed"
CHART_STATUS_UNINSTALLING = "uninstalling"
KUBE_STATUS_RUNNING = "running"
KUBE_STATUS_COMPLETED = "completed"
KUBE_STATUS_PENDING = "pending"
KUBE_STATUS_UNKNOWN = "unknown"


refresh_delay = 30
last_refresh_timestamp = None
update_running = False
global_charts_hashes = {}
global_extensions_dict_cached = []
global_collected_tgz_charts = {}


def execute_shell_command(command, shell=False, timeout=5):
    if ";" in command:
        err = f"Detected ';' in {command=} -> cancel request!"
        logger.error(err)
        return False, err
    logger.debug("executing shell command: {0}".format(command))
    logger.debug("shell={0} , timeout={1}".format(shell, timeout))
    command = [x for x in command.replace("  ", " ").split(" ") if x != ""]
    command_result = subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", shell=shell, timeout=timeout)

    stdout = command_result.stdout.strip()
    stderr = command_result.stderr.strip()
    return_code = command_result.returncode
    success = True if return_code == 0 else False

    if success:
        logger.debug("Command successful executed.")
        logger.debug(f"{return_code=}")
        logger.debug(f"{stdout=}")
        logger.debug(f"{stderr=}")
        return success, stdout

    else:
        logger.error("#######################################################################################################################################################")
        logger.error("")
        logger.error("ERROR while executing command: ")
        logger.error("")
        logger.error(f"COMMAND: {command}")
        logger.error("")
        logger.error("STDOUT:")
        for line in stdout.splitlines():
            logger.error(f"{line}")
        logger.error("")
        logger.error("STDERR:")
        for line in stderr.splitlines():
            logger.error(f"{line}")
        logger.error("")
        logger.error("#######################################################################################################################################################")
        return success, stderr


def get_extensions_list():
    global update_running, global_extensions_dict_cached, last_refresh_timestamp, refresh_delay
    logger.info(msg="In method: get_extensions_list()")

    if update_running or global_extensions_dict_cached == None or (last_refresh_timestamp != None and (time.time() - last_refresh_timestamp) < refresh_delay):
        logger.info("skipping scraping -> return global_extensions_dict_cached")
        return global_extensions_dict_cached

    logger.info("Generating new extension-list ...")

    global_extensions_dict = {}
    update_running = True
    available_extension_charts_tgz = collect_all_tgz_charts(
        keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
    deployed_extensions_dict = collect_helm_deployments()

    for extension_id, extension_dict in available_extension_charts_tgz.items():
        extension_installed = False
        latest_helm_status = None
        latest_kube_status = None
        extension_name = extension_dict["name"]
        if extension_name not in global_extensions_dict:
            logger.debug(
                f"Adding chart name to global_extensions_dict: {extension_name}")

            if 'kaapanaworkflow' in extension_dict['keywords']:
                extension_kind = 'dag'
            elif 'kaapanaapplication' in extension_dict['keywords']:
                extension_kind = 'application'
            else:
                logger.error(
                    f"Unknown 'extension['kind']' - {extension_id}: {extension_dict['keywords']}")
                continue

            global_extensions_dict[extension_name] = {
                "latest_version": None,
                "chart_name": extension_name,
                "available_versions": {},
                "description": extension_dict["description"],
                "keywords": extension_dict['keywords'],
                "experimental": 'yes' if 'kaapanaexperimental' in extension_dict['keywords'] else 'no',
                "multiinstallable": 'yes' if 'kaapanamultiinstallable' in extension_dict['keywords'] else 'no',
                "kind": extension_kind
            }

        if extension_dict["version"] not in global_extensions_dict[extension_name]["available_versions"]:
            logger.debug(
                f"Adding chart version {extension_name}: {extension_dict['version']}")

            deployments = []
            if extension_id in deployed_extensions_dict:
                for chart_deployment in deployed_extensions_dict[extension_id]:
                    extension_installed = True
                    chart_info = {
                        "deployment_id": chart_deployment["name"],
                        "helm_status": chart_deployment["status"],
                        "helm_info": chart_deployment,
                        "kube_status": KUBE_STATUS_UNKNOWN,
                        "kube_info": None,
                        "ready": False,
                        "links": []
                    }
                    latest_helm_status = chart_deployment["status"]
                    if chart_info["helm_status"] == CHART_STATUS_DEPLOYED:
                        success, deployment_ready, ingress_paths, concatenated_states = get_kube_objects(
                            chart_deployment["name"])
                        if success:
                            chart_info["kube_status"] = concatenated_states["status"]
                            chart_info["kube_info"] = concatenated_states
                            chart_info['links'] = ingress_paths
                            chart_info['ready'] = deployment_ready
                            latest_kube_status = concatenated_states["ready"]
                        else:
                            logger.error(
                                f"Could not request kube-state of: {chart_deployment['name']}")

                    elif chart_deployment["helm_status"] == CHART_STATUS_UNINSTALLING:
                        chart_info["kube_status"] = KUBE_STATUS_UNKNOWN
                        chart_info['links'] = []
                        chart_info['ready'] = False
                    else:
                        logger.error(
                            f"Unkown helm_status: {chart_deployment['helm_status']}")

                    deployments.append(chart_info)

            global_extensions_dict[extension_name]["available_versions"][extension_dict["version"]] = {
                "deployments": deployments,
            }
            global_extensions_dict[extension_name]["latest_version"] = sorted(list(
                global_extensions_dict[extension_name]["available_versions"].keys()), key=LooseVersion, reverse=True)[-1]
            logger.debug(json.dumps(
                global_extensions_dict[extension_name], indent=4))

        global_extensions_dict[extension_name]['installed'] = "yes" if extension_installed else "no"
        global_extensions_dict[extension_name]['helmStatus'] = latest_helm_status
        global_extensions_dict[extension_name]['kubeStatus'] = latest_kube_status
        global_extensions_dict[extension_name]['version'] = global_extensions_dict[extension_name]['latest_version']
        global_extensions_dict[extension_name]['versions'] = list(
            global_extensions_dict[extension_name]['available_versions'].keys())
        # global_extensions_dict[extension_name]['name'] = global_extensions_dict[extension_name]['releaseName']

    last_refresh_timestamp = time.time()
    update_running = False
    result_list = []
    for extension_name, extension_info in global_extensions_dict.items():
        for version, version_content in extension_info["available_versions"].items():
            if len(version_content["deployments"]) > 0:
                for deplyment in version_content["deployments"]:
                    chart_template = extension_info.copy()
                    chart_template["installed"] = "yes"
                    chart_template["releaseName"] = deplyment["deployment_id"]
                    chart_template["successful"] = "yes" if deplyment["ready"] else "pending"
                    chart_template["helmStatus"] = deplyment["helm_status"]
                    chart_template["kubeStatus"] = deplyment["kube_info"]["ready"]
                    result_list.append(chart_template)

                if extension_info["multiinstallable"] == "yes":
                    extension_info["installed"] = "no"
                    extension_info["helmStatus"] = ""
                    extension_info["kubeStatus"] = ""
                    extension_info["successful"] = ""
            else:
                extension_info["releaseName"] = extension_info["chart_name"]
                result_list.append(extension_info)

    global_extensions_dict_cached = result_list

    logger.debug("End of method: get_extensions_list()")
    return global_extensions_dict_cached


def collect_all_tgz_charts(keywords_filter):
    logger.debug(f"In method: collect_all_tgz_charts({ keywords_filter= })")
    global global_collected_tgz_charts

    keywords_filter = set(keywords_filter)
    chart_tgz_files = [f for f in glob.glob(
        os.path.join(settings.helm_extensions_cache, '*.tgz'))]
    for chart_tgz_file in chart_tgz_files:
        chart_hash = sha256sum(filepath=chart_tgz_file)
        if chart_tgz_file not in global_charts_hashes or chart_hash != global_charts_hashes[chart_tgz_file]:
            logger.info(
                f"Chart {basename(chart_tgz_file)} has been modified -> reading tgz!")

            helm_command = f'{settings.helm_path} show chart {chart_tgz_file}'
            logger.debug(f"Executing CMD: {helm_command}")
            success, stdout, stderr = execute_shell_command(helm_command)
            if success:
                logger.debug(f"sucess!")
                global_charts_hashes[chart_tgz_file] = chart_hash

                logger.debug(f"Loading chart yaml in dict ...")
                chart = list(yaml.load_all(stdout, yaml.FullLoader))[0]
                if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                    logger.debug(f"Valid keyword-filter!")
                    global_collected_tgz_charts[f'{chart["name"]}-{chart["version"]}'] = chart
                else:
                    logger.debug(
                        f"skipping due to keyword-filter - {keywords_filter=}")
            else:
                logger.error(f"execution not successful!")
        else:
            logger.debug(f"scraping not nessesary!")

    return global_collected_tgz_charts


def sha256sum(filepath):
    logger.debug(f"In method: sha256sum({filepath=})")
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])

    logger.debug(f"End method: sha256sum({filepath=})")
    return h.hexdigest()


def collect_helm_deployments(helm_namespace=settings.helm_namespace):
    logger.debug(f"In method: collect_helm_deployments({helm_namespace=})")
    deployed_charts_dict = {}
    success, stdout, stderr = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} ls --deployed --pending --failed --uninstalling --superseded -o json')
    if success:
        logger.debug(f"Success - got deployments.")
        namespace_deployments = json.loads(stdout)
        for chart in namespace_deployments:
            if chart["chart"] not in deployed_charts_dict:
                deployed_charts_dict[chart["chart"]] = [chart]
            else:
                deployed_charts_dict[chart["chart"]].append(chart)
    else:
        logger.error(f"Error - issue with get deployments.")

    logger.debug(f"End method: collect_helm_deployments({helm_namespace=})")
    return deployed_charts_dict


def get_kube_objects(release_name, helm_namespace=settings.helm_namespace):
    def get_kube_status(kind, name, namespace):
        states = None
        # Todo might be replaced by json or yaml output in the future with the flag -o json!
        success, stdout, stderr = execute_shell_command(
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
            logger.error(stderr)

        return states

    logger.debug(
        f"In method: get_kube_objects({release_name=}, {helm_namespace=})")
    success, stdout, stderr = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} get manifest {release_name}')
    ingress_paths = []
    concatenated_states = {
        "name": [],
        "ready": [],
        "status": [],
        "restarts": [],
        "age": []
    }
    if success:
        logger.debug(f"Success: get_kube_objects")
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
        logger.error(f"Error fetching kube-objects: {release_name=}")
        deployment_ready = False

    return success, deployment_ready, ingress_paths, concatenated_states
