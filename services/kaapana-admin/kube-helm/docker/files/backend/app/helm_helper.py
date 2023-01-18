import os
import glob
from os.path import basename
import yaml
import re
import json
import subprocess
import hashlib
import time
from distutils.version import LooseVersion

from typing import Dict, List, Set, Union, Tuple
from fastapi import UploadFile
from fastapi.logger import logger

from config import settings
import schemas

# TODO: get single extension
# TODO: get single tgz file

CHART_STATUS_UNDEPLOYED = "un-deployed"
CHART_STATUS_DEPLOYED = "deployed"
CHART_STATUS_FAILED = "failed"
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
global_extension_states: Dict[str, schemas.ExtensionState] = {}  # keys are in form <name>__<version>
global_recently_updated: Set[str] = set()  # list of keys for recently updated ( < refresh_delay) extensions


def execute_shell_command(command, shell=False, blocking=True, timeout=5, skip_check=False) -> Tuple[bool, str]:
    """Runs given command via subprocess.run or subprocess.Popen

    Args:
        command (_type_): _description_
        shell (bool, optional): _description_. Defaults to False.
        blocking (bool, optional): _description_. Defaults to True.
        timeout (int, optional): _description_. Defaults to 5.

    Returns:
        success (bool)  : whether the command ran successfully
        stdout  (str)   : output of the command. If success=False it is the same as stderr
    """
    if blocking is False:
        logger.info(f"running non-blocking {command=} via Popen, shell=True, timeout ignored")
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logger.debug(f"{p.pid=}")
        # TODO: add to a process queue, run p.communicate() & fetch returncode
        return True, ""

    if (not skip_check) and ";" in command:
        err = f"Detected ';' in blocking command {command} -> cancel request!"
        logger.error(err)
        return False, err
    logger.debug("executing blocking shell command: {0}".format(command))
    logger.debug("shell={0} , timeout={1}".format(shell, timeout))
    if "--timeout" in command:
        logger.debug("--timeout found in command, not passing a separate timeout")
        timeout = None
    if shell == False:
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


def add_extension_to_dict(
    extension_id: str,
    extension_dict: dict,
    global_extensions_dict: dict,
    deployed_extensions_dict: dict,
) -> dict:
    extension_installed = False
    latest_helm_status = None
    latest_kube_status = None
    extension_name = extension_dict["name"]
    if extension_name not in global_extensions_dict:
        # logger.debug(
        #     f"Adding chart name to global_extensions_dict: {extension_name}")

        if 'kaapanaworkflow' in extension_dict['keywords']:
            extension_kind = 'dag'
        elif 'kaapanaapplication' in extension_dict['keywords']:
            extension_kind = 'application'
        else:
            logger.error(
                f"Unknown 'extension['kind']' - {extension_id}: {extension_dict['keywords']}")
            return None

        ext_params = None
        if "extension_params" in extension_dict:
            logger.debug("add_extension_to_dict found extension_params")
            ext_params = extension_dict["extension_params"]
        global_extensions_dict[extension_name] = schemas.KaapanaExtension.construct(
            latest_version=None,
            chart_name=extension_name,
            name=extension_name,  # TODO: for backwards compat w/ landing page, delete later
            links=[],
            available_versions={},
            description=extension_dict["description"],
            keywords=extension_dict['keywords'],
            experimental='yes' if 'kaapanaexperimental' in extension_dict['keywords'] else 'no',
            multiinstallable='yes' if 'kaapanamultiinstallable' in extension_dict['keywords'] else 'no',
            kind=extension_kind,
            extension_params=ext_params,
            # "values": extension_dict["values"]
        )

    all_links = []
    if extension_dict["version"] not in global_extensions_dict[extension_name].available_versions:
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
                    success, deployment_ready, ingress_paths, concatenated_states = get_kube_objects(chart_deployment["name"])
                    if success:
                        chart_info["kube_status"] = concatenated_states["status"]
                        chart_info["kube_info"] = concatenated_states
                        chart_info['links'] = ingress_paths
                        chart_info['ready'] = deployment_ready
                        latest_kube_status = concatenated_states["ready"]
                        # all_links.extend(ingress_paths)
                    else:
                        logger.error(f"Could not request kube-state of: {chart_deployment['name']}")

                elif chart_info["helm_status"] == CHART_STATUS_FAILED:
                    chart_info["kube_status"] = KUBE_STATUS_UNKNOWN
                    chart_info["links"] = []
                    chart_info["ready"] = False

                elif chart_info["helm_status"] == CHART_STATUS_UNINSTALLING:
                    chart_info["kube_status"] = KUBE_STATUS_UNKNOWN
                    chart_info["links"] = []
                    chart_info["ready"] = False
                else:
                    logger.error(f"Unkown helm_status: {chart_info['helm_status']}") # failed is unknown?

                deployments.append(chart_info)

        logger.debug(f"adding {deployments=} as available versions to {global_extensions_dict[extension_name]}")
        available_versions = schemas.KaapanaAvailableVersions(
            deployments=deployments
        )
        global_extensions_dict[extension_name].available_versions[extension_dict["version"]] = available_versions
        global_extensions_dict[extension_name].latest_version = sorted(list(
            global_extensions_dict[extension_name].available_versions.keys()), key=LooseVersion, reverse=True)[-1]

    global_extensions_dict[extension_name].installed = "yes" if (extension_installed and global_extensions_dict[extension_name].multiinstallable == "no") else "no"
    global_extensions_dict[extension_name].helmStatus = latest_helm_status
    global_extensions_dict[extension_name].kubeStatus = latest_kube_status
    global_extensions_dict[extension_name].links = all_links
    global_extensions_dict[extension_name].version = global_extensions_dict[extension_name]['latest_version']
    global_extensions_dict[extension_name].versions = list(
        global_extensions_dict[extension_name].available_versions.keys())
    # global_extensions_dict[extension_name]['name'] = global_extensions_dict[extension_name]['releaseName']
    return global_extensions_dict


def add_info_from_deployments(
    extension_info: schemas.KaapanaExtension,
    result_list: List[schemas.KaapanaExtension]
):
    dep_exists = False

    for version, version_content in extension_info.available_versions.items():
        # logger.debug("extension_info.available_versions {0}".format(extension_info.available_versions))
        # logger.debug("version_content {0}".format(version_content))
        if len(version_content.deployments) > 0:
            dep_exists = True
            # go through deployment and pass info to extension level
            for deployment in version_content.deployments:
                chart_template = extension_info.copy()
                chart_template.installed = "yes"
                chart_template.releaseName = deployment.deployment_id
                chart_template.successful = "yes" if deployment.ready else "pending"
                chart_template.helmStatus = deployment.helm_status.capitalize()
                chart_template.kubeStatus = None
                chart_template.links = deployment.links
                if deployment.kube_info is not None:
                    chart_template.kubeStatus = [i.capitalize() for i in deployment.kube_info.status]

                result_list.append(chart_template)

            if extension_info.multiinstallable == "yes":
                extension_info.installed = "no"
                extension_info.helmStatus = ""
                extension_info.kubeStatus = ""
                extension_info.successful = ""
        else:
            # no deployments
            extension_info.releaseName = extension_info.chart_name
            # extension_info.installed = "no" # TODO: might be necessary
            result_list.append(extension_info)

    if dep_exists and extension_info.multiinstallable == "yes":
        extension_info.releaseName = extension_info.chart_name
        extension_info.installed = "no"
        result_list.append(extension_info)

    return result_list


def get_extensions_list() -> Union[List[schemas.KaapanaExtension], None]:
    """
    Fetches information about all chart tgz files under helm_extensions_cache 
    and all related kubernetes objects for deployed charts

    Returns:
        global_extensions_dict_cached (List[schemas.KaapanaExtension])
    """
    global update_running, global_extensions_dict_cached, last_refresh_timestamp, refresh_delay
    logger.info("getting extensions...")

    logger.debug("update_running {0}, global_extensions_dict_cached == None {1}, refresh {2}".format(
        update_running,
        global_extensions_dict_cached == None,
        (last_refresh_timestamp != None and (time.time() - last_refresh_timestamp) < refresh_delay)
    ))
    try:
        check = update_running or global_extensions_dict_cached == None or (last_refresh_timestamp != None and (time.time() - last_refresh_timestamp) < refresh_delay)
        global_extensions_dict: Dict[str, schemas.KaapanaExtension] = {}
        if settings.recent_update_cache and check:
            logger.info("using recent update cache")
            states_w_indexes = get_recently_updated_extensions()

            if len(states_w_indexes) == 0:
                # nothing updated recently, return cached
                logger.info(f"nothing updated recently -> return global_extensions_dict_cached, len: {len(global_extensions_dict_cached)}")
                return global_extensions_dict_cached

            elif len(states_w_indexes) > 0:
                logger.debug("updating cache, states_w_indexes {0}".format(states_w_indexes))
                # recent changes exist, update these in global extensions dict and return
                for ind, ext in states_w_indexes:
                    dep = collect_helm_deployments(chart_name=ext.chart_name)
                    tgz = collect_all_tgz_charts(
                        keywords_filter=['kaapanaapplication', 'kaapanaworkflow'],
                        name_filter=ext.chart_name+"-"+ext.version
                    )
                    if len(dep) > 1 or len(tgz) > 1:
                        logger.error("ERROR in recently_updated_states dep or tgz, dep: {0}, tgz: {1}".format(
                            dep, tgz))
                    extension_id, extension_dict = list(tgz.items())[0]
                    global_extensions_dict = add_extension_to_dict(
                        extension_id=extension_id,
                        extension_dict=extension_dict,
                        global_extensions_dict=global_extensions_dict,
                        deployed_extensions_dict=dep
                    )
                    # add to cache if a new extension is uploaded
                    if ind >= len(global_extensions_dict_cached):
                        global_extensions_dict_cached.append(global_extensions_dict[extension_dict["name"]])

                res: List[schemas.KaapanaExtension] = []
                for _, extension_info in global_extensions_dict.items():
                    res = add_info_from_deployments(
                        extension_info,
                        res
                    )

                # TODO: pass index from above to make the search redundant
                # TODO: make global_extensions_dict_cached actually a Dict so that double loop isn't necessary
                for i, ext in enumerate(global_extensions_dict_cached):
                    for j, rec_upd_ext in enumerate(res):
                        if ext.releaseName == rec_upd_ext.releaseName:
                            global_extensions_dict_cached[i] = rec_upd_ext
                            logger.debug(
                                "value updated in global_extensions_dict_cached from {0} to {1}".format(
                                    ext, rec_upd_ext
                                ))
                logger.debug(f"{len(global_extensions_dict_cached)=}")
                return global_extensions_dict_cached

        if check:
            # TODO: becomes redundant if setting.recent_update_cache option is the default
            # nothing updated recently, return cached
            logger.info("skipping list generation -> return global_extensions_dict_cached")
            return global_extensions_dict_cached

        # generate new list
        logger.info("Generating new extension-list ...")

        update_running = True
        available_extension_charts_tgz = collect_all_tgz_charts(
            keywords_filter=['kaapanaapplication', 'kaapanaworkflow'])
        deployed_extensions_dict = collect_helm_deployments()

        for extension_id, extension_dict in available_extension_charts_tgz.items():
            global_extensions_dict = add_extension_to_dict(
                extension_id=extension_id,
                extension_dict=extension_dict,
                global_extensions_dict=global_extensions_dict,
                deployed_extensions_dict=deployed_extensions_dict
            )

        last_refresh_timestamp = time.time()
        update_running = False
        result_list = []

        # set everything in KaapanaExtension object
        for _, extension_info in global_extensions_dict.items():
            result_list = add_info_from_deployments(
                extension_info,
                result_list
            )

        global_extensions_dict_cached = result_list

    except Exception as e:
        logger.error(e)
        update_running = False

    return global_extensions_dict_cached


def collect_all_tgz_charts(keywords_filter: List, name_filter: str = "") -> Dict[str, Dict]:
    """
    Gets the result of "helm show chart" for all tgz files under helm_extensions_cache

    Arguments:
        keywords_filter (List): keywords used for filtering fetched charts
        name_filter (str): the name of the chart

    Returns:
        global_collected_tgz_charts (Dict[str, Dict]): format for keys is `chart['name']}-{chart['version']`
    """
    logger.debug("collect_all_tgz_charts with keyword filter: {0}, name filter: {1}".format(
        keywords_filter,
        name_filter
    ))
    global global_collected_tgz_charts, global_charts_hashes

    keywords_filter = set(keywords_filter)
    name_filter = name_filter
    chart_tgz_files = [f for f in glob.glob(
        os.path.join(settings.helm_extensions_cache, '*.tgz')) if name_filter in f]
    logger.debug("found chart tgz files length: {0}".format(chart_tgz_files, ))
    logger.debug("global_charts_hashes length: {0}".format(global_charts_hashes))
    collected_tgz_charts: dict = {}
    for chart_tgz_file in chart_tgz_files:
        chart_hash = sha256sum(filepath=chart_tgz_file)
        if chart_tgz_file not in global_charts_hashes or chart_hash != global_charts_hashes[chart_tgz_file]:
            logger.info(
                f"Chart {basename(chart_tgz_file)} has been modified -> reading tgz!")

            helm_command = f'{settings.helm_path} show chart {chart_tgz_file}'
            success, stdout = execute_shell_command(helm_command)
            if success:
                global_charts_hashes[chart_tgz_file] = chart_hash

                logger.debug(f"Loading chart yaml in dict ...")
                chart = list(yaml.load_all(stdout, yaml.FullLoader))[0]
                if 'keywords' in chart and (set(chart['keywords']) & keywords_filter):
                    logger.debug(f"Valid keyword-filter!")
                    chart = add_extension_params(chart)
                    global_collected_tgz_charts[f'{chart["name"]}-{chart["version"]}'] = chart
                    collected_tgz_charts[f'{chart["name"]}-{chart["version"]}'] = chart
                else:
                    logger.debug(
                        f"skipping due to keyword-filter - {keywords_filter=}")
            else:
                logger.error(f"execution not successful!")
        else:
            logger.debug(f"scraping not necessary!")

    # file is deleted, remove from hashes and global_collected_tgz_charts
    # TODO: this is messy, handle this in an endpoint like (/file-delete)
    set_files = set(chart_tgz_files)
    if name_filter == "" and len(global_charts_hashes) > len(set_files):
        hash_keys = set(global_charts_hashes.keys())
        diff = hash_keys.difference(set_files)
        logger.info(f"File(s) removed from the folder, {hash_keys=}, {set_files=}, {diff=}")
        for f in diff:
            logger.info(f"Deleting hash and chart info for file {f}")
            global_charts_hashes.pop(f)
            fname = ".".join(f.split("/")[-1].split(".")[:-1])
            global_collected_tgz_charts.pop(fname)

    logger.debug(f"{global_collected_tgz_charts=}")
    if name_filter != "":
        if len(collected_tgz_charts) > 0:
            logger.debug("returning collected_tgz_charts {0}".format(collected_tgz_charts))
            return collected_tgz_charts

        if name_filter in global_collected_tgz_charts:
            chart_dict = {name_filter: global_collected_tgz_charts[name_filter]}
            logger.debug("returning {0}".format(chart_dict))
            return chart_dict

    return global_collected_tgz_charts


def sha256sum(filepath) -> str:
    # logger.debug(f"In method: sha256sum({filepath=})")
    h = hashlib.sha256()
    b = bytearray(128*1024)
    mv = memoryview(b)
    with open(filepath, 'rb', buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])

    # logger.debug(f"End method: sha256sum({filepath=})")
    return h.hexdigest()


def collect_helm_deployments(helm_namespace: str = settings.helm_namespace, chart_name: str = None) -> Dict[str, Dict]:
    """
    Gets all deployed helm charts independent of their status

    Arguments:
        helm_namespace (str): Namespace for helm commands

    Returns:
        deployed_charts_dict (Dict[str, Dict]): format for keys is `chart['chart']`

    """
    deployed_charts_dict = {}
    cmd = f'{settings.helm_path} -n {helm_namespace} ls --deployed --pending --failed --uninstalling --superseded -o json'
    success, stdout = execute_shell_command(cmd)
    if success:
        logger.debug(f"Success - got deployments.")
        namespace_deployments = json.loads(stdout)
        for chart in namespace_deployments:
            if chart_name is not None and chart_name != chart["name"]:
                continue

            if chart["chart"] not in deployed_charts_dict:
                deployed_charts_dict[chart["chart"]] = [chart]
            else:
                deployed_charts_dict[chart["chart"]].append(chart)
    else:
        logger.error(f"Error - issue with get deployments.")

    return deployed_charts_dict


def get_kube_objects(release_name: str, helm_namespace: str = settings.helm_namespace) -> Tuple[bool, bool, List[str], schemas.KubeInfo]:
    """
    Gets information about all kube objects in helm manifest

    Arguments:
        release_name    (str): Name of the helm chart
        helm_namespace  (str): Namespace for helm commands

    Returns:
        success             (bool)             : whether the helm command ran successfully
        deployment_ready    (bool)             : whether all kube objects are in "Running" or "Completed" states
        ingress_paths       (List[str])        : paths extracted from ingress objects
        concatenated_states (schemas.KubeInfo]): contains all information about related kube objects 
    """
    def get_kube_status(kind, name, namespace) -> Union[schemas.KubeInfo, None]:
        """
        Returns pod information as KubeInfo
        """
        states = None
        # TODO: might be replaced by json or yaml output in the future with the flag -o json!
        success, stdout = execute_shell_command(
            f"{settings.kubectl_path} -n {namespace} get pod -l={kind}-name={name}")
        if success:
            states = schemas.KubeInfo(
                name=[],
                ready=[],
                status=[],
                restarts=[],
                age=[]
            )

            stdout = stdout.splitlines()[1:]
            for row in stdout:
                name, ready, status, restarts, age = re.split('\s\s+', row)
                states.name.append(name)
                states.ready.append(ready)
                states.status.append(status.lower())
                states.restarts.append(restarts)
                states.age.append(age)
        else:
            logger.error(f'Could not get kube status of {name}')
            logger.error(stdout)

        return states

    logger.debug(
        f"get_kube_objects for ({release_name=}, {helm_namespace=})")
    success, stdout = execute_shell_command(
        f'{settings.helm_path} -n {helm_namespace} get manifest {release_name}')
    ingress_paths = []
    concatenated_states = schemas.KubeInfo(
        name=[],
        ready=[],
        status=[],
        restarts=[],
        age=[]
    )
    if success:
        logger.debug(f"Success: get_kube_objects")
        manifest_dict = list(yaml.load_all(stdout, yaml.FullLoader))
        deployment_ready = True

        # convert configs inside chart's manifest to concatenated KubeInfo
        for config in manifest_dict:
            if config is None:
                continue
            if config['kind'] == 'Ingress':
                ingress_path = config['spec']['rules'][0]['http']['paths'][0]['path']
                ingress_paths.append(ingress_path)

            elif config['kind'] == 'Deployment' or config['kind'] == 'Job':
                obj_kube_status = None
                if config['kind'] == 'Deployment':
                    obj_kube_status = get_kube_status(
                        'app', config['spec']['selector']['matchLabels']['app-name'], config['metadata']['namespace'])
                elif config['kind'] == 'Job':
                    obj_kube_status = get_kube_status(
                        'job', config['metadata']['name'], config['metadata']['namespace'])

                if obj_kube_status != None:
                    for key, value in obj_kube_status.dict().items():
                        concatenated_states[key].extend(value)
                        logger.info(f"{key=} {value=}")
                        if key == "status" and value[0] != KUBE_STATUS_COMPLETED and value[0] != KUBE_STATUS_RUNNING:
                            deployment_ready = False
    else:
        logger.error(f"Error fetching kube-objects: {release_name=}")
        deployment_ready = False

    return success, deployment_ready, ingress_paths, concatenated_states


def helm_show_values(name, version) -> Dict:
    """
    Returns result of 'helm show values' for tgz file
    """
    success, stdout = execute_shell_command(
        f'{settings.helm_path} show values {settings.helm_extensions_cache}/{name}-{version}.tgz')
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        return {}


def helm_repo_index(repo_dir):
    helm_command = f'{settings.helm_path} repo index {repo_dir}'
    _, _ = execute_shell_command(helm_command)


def helm_show_chart(name=None, version=None, package=None) -> Dict:
    """
    Returns result of 'helm show chart' for package, if it is availabe. Otherwise runs for the tgz file
    """
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


def update_extension_state(state: schemas.ExtensionStateUpdate = None):
    """
    writes to global_extension_states, appends to global_recently_updated if necessary
    """
    global global_extension_states, global_recently_updated

    logger.debug(f"in function: update_extension_state, {state}=")

    if len(global_extension_states) == 0 and state is None:
        # initialize state dict
        for ext in global_extensions_dict_cached:
            for v in ext["available_versions"]:
                state = schemas.ExtensionStateType.NOT_INSTALLED
                if len(ext["available_versions"][v]["deployments"]) > 0:
                    state = schemas.ExtensionStateType.INSTALLED

                key = ext["chart_name"] + "__" + v
                global_extension_states[key] = schemas.ExtensionState.construct(
                    extension_name=ext.chart_name,
                    extension_version=v,
                    state=state,
                    update_time=time.time(),
                    last_read_time=time.time(),
                    recently_updated=False  # since it's the initialization
                )
        return

    if state is None:
        logger.error("update_extension_state got an empty state object")
        return

    name = state["extension_name"]
    version = state["extension_version"]
    key = name + "__" + version
    if key not in global_extension_states:
        logger.warning("{0} is not already in global_extension_states, adding a new entry".format(key))
        global_extension_states[key] = schemas.ExtensionState.construct(
            extension_name=name,
            extension_version=version,
            state=state.state,
            update_time=time.time(),
            last_read_time=time.time(),
            recently_updated=True,
        )
    else:
        logger.debug("{0} is already in global_extension_states, updating".format(key))
        ext = global_extension_states[key]
        logger.debug("before update {0}".format(ext))
        prev_state = ext.state
        logger.info(f"updating extension state to {0} from {1}".format(state.state, prev_state))
        ext.update_time = time.time()
        ext.last_read_time = time.time()
        ext.recently_updated = True
        logger.debug("after update {0}".format(ext))
    global_recently_updated.add(key)


def get_recently_updated_extensions() -> List[schemas.KaapanaExtension]:
    """
    get states for keys in recently_updated set  
    """
    global global_extension_states, global_recently_updated, global_extensions_dict_cached
    res: List[Tuple[int, schemas.KaapanaExtension]] = []
    to_remove = []
    logger.debug("get_recently_updated_extensions called with global_recently_updated {0}".format(global_recently_updated))
    for key in global_recently_updated:
        ext_state = global_extension_states[key]
        # TODO: instead of this, update the extension in global_extensions_dict_cached
        for i, ext in enumerate(global_extensions_dict_cached):
            if ext.releaseName == ext_state.extension_name:
                res.append((i, global_extensions_dict_cached[i]))
        if len(res) > 1:
            logger.error("Found more than one matching charts for {0} in cached extensions dict".format(ext_state.extension_name))
        elif len(res) == 0:
            # found new chart
            logger.info("New chart {0}".format(ext_state.extension_name))
            fname, version = key.split("__")
            name = '-'.join(fname[:-4].split("-")[0:-1])
            res.append(
                (
                    len(global_extensions_dict_cached),
                    schemas.KaapanaExtension.construct(
                        chart_name=name,
                        version=version)
                )
            )
            to_remove.append(key)

        ext_state.last_read_time = time.time()
        # if not longer recent, update its state and remove from set
        if ext_state["last_read_time"] - ext_state["update_time"] > refresh_delay:
            ext_state.recently_updated = False
            to_remove.append(key)

    # remove the ones that are not recently updated anymore
    for k in to_remove:
        if k in global_recently_updated:
            global_recently_updated.remove(k)

    return res


def add_extension_params(chart):
    """
    Add 'extension_params' to chart object, if a valid field exists in chart values.
    """
    logger.debug(f"in function add_extension_params {chart['name']=}")
    vals = helm_show_values(chart["name"], chart["version"])
    if (vals is not None) and "extension_params" in vals:
        # TODO: validate the parameter field
        logger.debug("in if")
        if ";" not in vals["extension_params"]:
            chart["extension_params"] = vals["extension_params"]
    return chart
