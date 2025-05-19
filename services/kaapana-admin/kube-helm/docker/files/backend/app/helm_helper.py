import asyncio
import glob
import hashlib
import json
import os
import re
import fnmatch
import subprocess
import time
from distutils.version import LooseVersion
from os.path import basename
from typing import Dict, List, Set, Tuple, Union
from utils import helm_get_values

import schemas
import yaml
from config import settings, timeouts
from logger import get_logger

logger = get_logger(__name__)

CHART_STATUS_UNDEPLOYED = "un-deployed"
CHART_STATUS_DEPLOYED = "deployed"
CHART_STATUS_FAILED = "failed"
CHART_STATUS_UNINSTALLING = "uninstalling"
KUBE_STATUS_RUNNING = "running"
KUBE_STATUS_COMPLETED = "completed"
KUBE_STATUS_PENDING = "pending"
KUBE_STATUS_UNKNOWN = "unknown"


REFRESH_DELAY = 30
last_refresh_timestamp = None
last_refresh_timestamp_platforms = None
update_running = False
global_charts_hashes = {}
global_charts_hashes_platforms = {}
global_extensions_list = []
global_platforms_list = []
global_collected_tgz_charts = {}
global_collected_tgz_charts_platforms = {}
global_extension_states: Dict[str, schemas.ExtensionState] = (
    {}
)  # keys are in form <name>__<version>
global_recently_updated: Set[str] = (
    set()
)  # list of keys for recently updated ( < REFRESH_DELAY) extensions
global_extensions_release_names: Set[str] = set()


async def exec_shell_cmd_async(
    command, shell=False, timeout: int = timeouts.shell_cmd_default_timeout
) -> Tuple[bool, str]:
    """Runs given command via asyncio.create_subprocess_shell()

    Args:
        command (_type_): _description_
        shell (bool, optional): _description_. Defaults to False.
        timeout (int, optional): _description_. Defaults to 5.

    Returns:
        success (bool)  : whether the command ran successfully
        stdout  (str)   : output of the command. If success=False it is the same as stderr
    """
    logger.debug(f"executing ASYNC shell command: {command}")
    logger.debug(f"{shell=} , {timeout=}")
    try:
        if shell == False and (type(command) is str):
            command = [x for x in command.replace("  ", " ").split(" ") if x != ""]

        command_result = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            shell=shell,
        )

        stdout, stderr = await asyncio.wait_for(
            command_result.communicate(), timeout=timeout
        )
        if command_result.returncode == 0:
            logger.debug(f"Command successfully executed {command}")
            out = stdout.decode()
            return True, out
        else:
            err = stderr.decode()
            logger.error(f"ERROR while executing command: {err}")
            logger.error(f"COMMAND: {command}")
            return False, err

    except asyncio.TimeoutError as e:
        logger.error(f"Command timed out after {timeout} seconds")
        return False, f"Command timed out after {timeout} seconds"

    except Exception as e:
        logger.error(str(e))
        return False, str(e)


def execute_shell_command(
    command, shell=False, blocking=True, timeout=timeouts.shell_cmd_default_timeout, skip_check=False
) -> Tuple[bool, str]:
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
        logger.debug(
            f"running non-blocking {command=} via Popen, shell=True, timeout ignored"
        )
        p = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        logger.debug(f"{p.pid=}")
        # TODO: add to a process queue, run p.communicate() & fetch returncode
        return True, ""

    # if (not skip_check) and ";" in command:
    #     err = f"Detected ';' in blocking command {command} -> cancel request!"
    #     logger.error(err)
    #     return False, err
    logger.debug(f"executing blocking shell command: {command}")
    logger.debug(f"{shell=} , {timeout=}")
    if "--timeout" in command:
        logger.debug("--timeout found in command, not passing a separate timeout")
        timeout = None
    if shell == False:
        command = [x for x in command.replace("  ", " ").split(" ") if x != ""]
    command_result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        shell=shell,
        timeout=timeout,
    )

    stdout = command_result.stdout.strip()
    stderr = command_result.stderr.strip()
    return_code = command_result.returncode
    success = True if return_code == 0 and stderr == "" else False

    if success:
        logger.debug(f"Command successfully executed {command}")
        logger.debug(f"{return_code=}")
        logger.debug(f"{stdout=}")
        logger.debug(f"{stderr=}")
        return success, stdout
    elif command[3] == "status":
        logger.debug(
            f"Ignoring error, since we just wanted to check if chart is installed {command}"
        )
        logger.debug(f"{return_code=}")
        logger.debug(f"{stdout=}")
        logger.debug(f"{stderr=}")
        return success, stderr
    else:
        logger.error("ERROR while executing command: ")
        logger.error(f"COMMAND: {command}")
        logger.error("STDOUT:")
        for line in stdout.splitlines():
            logger.error(f"{line}")
        logger.error("")
        logger.error("STDERR:")
        for line in stderr.splitlines():
            logger.error(f"{line}")
        logger.error("")
        return success, stderr

def check_if_extension_param_is_needed(
    extension_name: str,
    ext_params: dict,
) -> dict:      
    """
    Checks if the extension_params are needed for the extension by comparing them with the global values
    Args:
        ext_params (dict): The extension parameters to check
    Returns:
        dict: The updated extension parameters
    """

    #get global values
    exctension_values = helm_get_values("kaapana-admin-chart","default")
    for key in ext_params:
        if key in exctension_values.get("global", {}):
            ext_params[key]["required"] = False
        else:
            ext_params[key]["required"] = True

    return ext_params

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
    logger.debug(f"in function add_extension_dict {extension_id=} {extension_dict=}")
    if extension_name not in global_extensions_dict:
        if "kaapanaworkflow" in extension_dict["keywords"]:
            extension_kind = "dag"
        elif "kaapanaapplication" in extension_dict["keywords"]:
            extension_kind = "application"
        elif "kaapanaplatform" in extension_dict["keywords"]:
            extension_kind = "platform"
        else:
            logger.error(
                f"Unknown extension['kind'] - {extension_id}: {extension_dict['keywords']}"
            )
            return None

        ext_params = None
        if "extension_params" in extension_dict:
            logger.debug("add_extension_to_dict found extension_params")
            ext_params = extension_dict["extension_params"]
            ext_params = check_if_extension_param_is_needed(extension_name, ext_params)
        global_extensions_dict[extension_name] = (
            schemas.KaapanaExtension.model_construct(
                latest_version=None,
                chart_name=extension_name,
                name=extension_name,  # TODO: for backwards compat w/ landing page, delete later
                links=[],
                available_versions={},
                description=extension_dict["description"],
                keywords=extension_dict["keywords"],
                experimental=(
                    "yes"
                    if "kaapanaexperimental" in extension_dict["keywords"]
                    else "no"
                ),
                multiinstallable=(
                    "yes"
                    if "kaapanamultiinstallable" in extension_dict["keywords"]
                    else "no"
                ),
                kind=extension_kind,
                resourceRequirement=(
                    "gpu" if "gpurequired" in extension_dict["keywords"] else "cpu"
                ),
                extension_params=ext_params,
                annotations=extension_dict.get("annotations"),
                # "values": extension_dict["values"]
            )
        )

    all_links = []
    if (
        extension_dict["version"]
        not in global_extensions_dict[extension_name].available_versions
    ):
        logger.debug(
            f"Adding chart version {extension_name}: {extension_dict['version']}"
        )

        deployments = []
        if extension_id in deployed_extensions_dict:
            for chart_deployment in deployed_extensions_dict[extension_id]:
                try:
                    extension_installed = True
                    chart_info = {
                        "deployment_id": chart_deployment["name"],
                        "helm_status": chart_deployment["status"],
                        "helm_info": chart_deployment,
                        "kube_status": KUBE_STATUS_UNKNOWN,
                        "kube_info": None,
                        "ready": False,
                        "links": [],
                    }
                    latest_helm_status = chart_deployment["status"]
                    if chart_info["helm_status"] == CHART_STATUS_DEPLOYED:
                        (
                            success,
                            deployment_ready,
                            paths,
                            concatenated_states,
                        ) = get_kube_objects(
                            chart_deployment["name"], chart_deployment["namespace"]
                        )
                        if success:
                            chart_info["kube_status"] = concatenated_states["status"]
                            chart_info["kube_info"] = concatenated_states
                            chart_info["links"] = (
                                extension_dict["links"]
                                if "links" in extension_dict
                                else paths
                            )
                            chart_info["ready"] = deployment_ready
                            latest_kube_status = concatenated_states["ready"]
                            # all_links.extend(paths)
                        else:
                            logger.error(
                                f"Could not request kube-state of: {chart_deployment['name']}"
                            )
                    elif chart_info["helm_status"] == CHART_STATUS_UNINSTALLING:
                        chart_info["kube_status"] = KUBE_STATUS_UNKNOWN
                        chart_info["links"] = []
                        chart_info["ready"] = False
                    elif chart_info["helm_status"] == "failed":
                        chart_info["kube_status"] = ""
                        chart_info["links"] = []
                        chart_info["ready"] = False
                    else:
                        logger.error(
                            f"Unknown helm_status: {chart_info['helm_status']}"
                        )

                    deployments.append(chart_info)

                except Exception as e:
                    logger.error(
                        f"Skipping chart {chart_deployment['name']}-{chart_deployment['version']} , error: {str(e)}"
                    )

        available_versions = schemas.KaapanaAvailableVersions(deployments=deployments)
        global_extensions_dict[extension_name].available_versions[
            extension_dict["version"]
        ] = available_versions
        global_extensions_dict[extension_name].latest_version = sorted(
            list(global_extensions_dict[extension_name].available_versions.keys()),
            key=LooseVersion,
            reverse=True,
        )[0]

    global_extensions_dict[extension_name].installed = (
        "yes"
        if (
            extension_installed
            and global_extensions_dict[extension_name].multiinstallable == "no"
        )
        else "no"
    )
    global_extensions_dict[extension_name].helmStatus = (
        latest_helm_status
        if (latest_helm_status is None)
        else latest_helm_status.capitalize()
    )
    global_extensions_dict[extension_name].kubeStatus = latest_kube_status
    global_extensions_dict[extension_name].links = all_links
    global_extensions_dict[extension_name].version = global_extensions_dict[
        extension_name
    ]["latest_version"]
    global_extensions_dict[extension_name].versions = sorted(
        list(global_extensions_dict[extension_name].available_versions.keys()),
        reverse=True,
        key=LooseVersion,
    )
    # global_extensions_dict[extension_name]['name'] = global_extensions_dict[extension_name]['releaseName']

    return global_extensions_dict


def add_info_from_deployments(
    extension_info: schemas.KaapanaExtension,
    result_list: List[schemas.KaapanaExtension],
):
    dep_exists = False
    init_len = len(result_list)
    logger.debug(f"{extension_info.chart_name=}")
    for version, version_content in extension_info.available_versions.items():
        if len(version_content.deployments) > 0:
            dep_exists = True
            # if multiinstallable and a launched app, create new extension
            if extension_info.multiinstallable == "yes":
                for deployment in version_content.deployments:
                    chart_template = extension_info.copy()
                    chart_template.installed = "yes"
                    chart_template.releaseName = deployment.deployment_id
                    chart_template.successful = "yes" if deployment.ready else "pending"
                    chart_template.helmStatus = deployment.helm_status.capitalize()
                    chart_template.kubeStatus = None
                    # TODO: rm "kaapanaint" workaround
                    chart_template.links = deployment.links
                    chart_template.version = version
                    chart_template.latest_version = version
                    chart_template.versions = [version]
                    if deployment.kube_info is not None:
                        chart_template.kubeStatus = [
                            i.capitalize() for i in deployment.kube_info.status
                        ]

                    result_list.append(chart_template)

                extension_info.installed = "no"
                extension_info.helmStatus = ""
                extension_info.kubeStatus = ""
                extension_info.successful = ""
            else:
                for deployment in version_content.deployments:
                    extension_info.links.extend(
                        [link for link in deployment.links if "kaapanaint" not in link]
                    )
                extension_info.installed = "yes"
        else:
            # no deployments
            extension_info.releaseName = extension_info.chart_name
            # extension_info.installed = "no" # TODO: might be necessary

    extension_info.releaseName = extension_info.chart_name
    result_list.append(extension_info)

    # if dep_exists and extension_info.multiinstallable == "yes":
    #     extension_info.releaseName = extension_info.chart_name
    #     extension_info.installed = "no"
    #     result_list.append(extension_info)
    if len(result_list) - init_len > 1:
        logger.warning(f"multiple extensions added for {extension_info.releaseName}")
    return result_list

    # import debugpy
    # debugpy.listen(("localhost", 17777))
    # debugpy.wait_for_client()
    # debugpy.breakpoint()


def get_extensions_list() -> Union[List[schemas.KaapanaExtension], None]:
    """
    Fetches information about application and workflow chart tgz files under helm_extensions_cache
    and all related kubernetes objects for deployed charts

    Returns:
        (List[schemas.KaapanaExtension])
    """
    global update_running, global_extensions_list, last_refresh_timestamp, global_extensions_release_names
    logger.info("getting extensions...")
    keywords_filter = ["kaapanaapplication", "kaapanaworkflow"]
    
    try:
        logger.info(f"update_running: {update_running}")
        logger.info(f"last_refresh_timestamp: {last_refresh_timestamp}")
        if last_refresh_timestamp is not None:
            logger.info(f"time since last refresh: {time.time() - last_refresh_timestamp:.2f} seconds")
        logger.info(f"refresh delay: {REFRESH_DELAY}")
        # Check if we need a refresh
        needs_refresh = (
            not update_running 
            and (
                not global_extensions_list 
                or last_refresh_timestamp is None 
                or (time.time() - last_refresh_timestamp) >= REFRESH_DELAY
            )
        )

        if not needs_refresh:
            logger.info("skipping list generation -> returning cached list")
            return global_extensions_list

        
        # Check  for recently updated extensions
        if settings.recent_update_cache:
            global_extensions_list = update_recently_changed_extensions(keywords_filter)
            if global_extensions_list:
                return global_extensions_list

        # Generate a completely new list
        logger.info("Generating new extension-list ...")
        last_refresh_timestamp = time.time()
        result_list = generate_fresh_extensions_list(keywords_filter)
        global_extensions_release_names = set()
        # Filter out duplicates by releaseName
        filtered_result_list = []
        for r in result_list:
            if r.releaseName not in global_extensions_release_names:
                filtered_result_list.append(r)
                global_extensions_release_names.add(r.releaseName)
            else:
                logger.info(f"excluding {r.releaseName} from the list, already exists in the set of release names")
        
        global_extensions_list = filtered_result_list
        return global_extensions_list
        
    except Exception as e:
        logger.error(e)
        update_running = False
        raise Exception(e)


def get_platforms_list() -> Union[List[schemas.KaapanaExtension], None]:
    """
    Fetches information about platform chart tgz files under helm_extensions_cache
    and all related kubernetes objects for deployed charts

    Returns:
        (List[schemas.KaapanaExtension])
    """
    global update_running, global_platforms_list, last_refresh_timestamp_platforms
    keywords_filter = ["kaapanaplatform"]
    
    try:

        # Check if we need a refresh
        needs_refresh = (
            not update_running 
            and (
                not global_platforms_list 
                or last_refresh_timestamp_platforms is None 
                or (time.time() - last_refresh_timestamp_platforms) >= REFRESH_DELAY
            )
        )

        if not needs_refresh:
            #logger.debug("skipping platform list generation -> returning cached list")
            return global_platforms_list
        
        # Generate a completely new list
        logger.info("Generating new platforms-list ...")
        last_refresh_timestamp_platforms = time.time()
        global_platforms_list = generate_fresh_extensions_list(keywords_filter=keywords_filter, platforms=True)
        return global_platforms_list
        
    except Exception as e:
        logger.error(e)
        update_running = False
        raise Exception(e)

def update_recently_changed_extensions(keywords_filter: List) -> Union[List[schemas.KaapanaExtension], None]:
    """
    Updates only the extensions that have changed recently
    Args:
        keywords_filter (List): List of keywords to filter extensions by
    Returns:
        List[schemas.KaapanaExtension] or None if no recent updates
    """     
    global update_running, global_extensions_list, global_extensions_release_names

    states_w_indexes = get_recently_updated_extensions()
    
    if len(states_w_indexes) == 0:
        # nothing updated recently, return cached
        logger.info(f"no recent updates -> returning cached list")
        return global_extensions_list
    
    logger.info(f"updating recently updated cache, {len(states_w_indexes)=}")
    
    # Recent changes exist, update these in global extensions dict and return
    global_extensions_dict: Dict[str, schemas.KaapanaExtension] = {}
    
    for ind, ext in states_w_indexes:
        chart_name = ext.releaseName if ext.multiinstallable == "yes" else ext.chart_name
        
        dep = collect_helm_deployments(chart_name=chart_name, platforms=False)
        tgz = collect_all_tgz_charts(
            keywords_filter=keywords_filter,
            name_filter=ext.chart_name + "-" + ext.version,
        )
        
        if len(dep) > 1 or len(tgz) > 1:
            logger.error(f"ERROR in recently_updated_states dep or tgz, {dep.keys()}, {tgz.keys()}")
            logger.debug(f"{dep=}, {tgz=}")
            
        extension_id, extension_dict = list(tgz.items())[0]
        global_extensions_dict = add_extension_to_dict(
            extension_id=extension_id,
            extension_dict=extension_dict,
            global_extensions_dict=global_extensions_dict,
            deployed_extensions_dict=dep,
        )
        
        # Add to cache if a new extension is uploaded
        if ind >= len(global_extensions_list):
            extension = global_extensions_dict[extension_dict["name"]]
            name = extension.chart_name
            if name in global_extensions_release_names:
                logger.info(f"{name} already in the list, avoiding duplicate entries")
            else:
                global_extensions_list.append(name)
                global_extensions_release_names.add(name.releaseName)

    # Convert dictionary to list format
    res: List[schemas.KaapanaExtension] = []
    for _, extension_info in global_extensions_dict.items():
        res = add_info_from_deployments(
            extension_info,
            res,
        )

    # TODO: pass index from above to make the search redundant
    # TODO: make global_extensions_list actually a Dict so that double loop isn't necessary
    # Update global_extensions_list with new information
    for i, ext in enumerate(global_extensions_list):
        for j, rec_upd_ext in enumerate(res):
            if ext.releaseName == rec_upd_ext.releaseName:
                global_extensions_list[i] = rec_upd_ext
                logger.debug(f"value updated in global_extensions_list from {ext} to {rec_upd_ext}")
    
    logger.debug(f"{len(global_extensions_list)=}")
    return global_extensions_list


def generate_fresh_extensions_list(keywords_filter, platforms: bool = False) -> List[schemas.KaapanaExtension]:
    """
    Generates a completely new list of extensions
    
    Args:
        platforms (bool): If True, fetch platform extensions, otherwise fetch applications and workflows
        keywords_filter (list): List of keywords to filter extensions by
        
    Returns:
        List[schemas.KaapanaExtension]
    """
    global update_running 
    
    update_running = True
    # Collect available charts and deployed extensions
    available_extension_charts_tgz = collect_all_tgz_charts(keywords_filter=keywords_filter)
    deployed_extensions_dict = collect_helm_deployments(platforms=platforms)
    
    # Build extension dictionary
    global_extensions_dict: Dict[str, schemas.KaapanaExtension] = {}
    for extension_id, extension_dict in available_extension_charts_tgz.items():
        global_extensions_dict = add_extension_to_dict(
            extension_id=extension_id,
            extension_dict=extension_dict,
            global_extensions_dict=global_extensions_dict,
            deployed_extensions_dict=deployed_extensions_dict,
        )
        
    # Convert dictionary to list format
    update_running = False
    result_list = []
    for _, extension_info in global_extensions_dict.items():
        result_list = add_info_from_deployments(extension_info, result_list)
    
    return result_list

        


def collect_all_tgz_charts(
    keywords_filter: List, name_filter: str = ""
) -> Dict[str, Dict]:
    """
    Gets the result of "helm show chart" for all tgz files under helm_extensions_cache

    Arguments:
        keywords_filter (List): keywords used for filtering fetched charts
        name_filter (str): the name of the chart

    Returns:
        global_collected_tgz_charts (Dict[str, Dict]): format for keys is `chart['name']}-{chart['version']`
    """
    logger.debug(f"collect_all_tgz_charts with {keywords_filter=}, {name_filter=}")
    global global_collected_tgz_charts, global_collected_tgz_charts_platforms, global_charts_hashes, global_charts_hashes_platforms
    current_hash = global_charts_hashes
    current_tgz_charts = global_collected_tgz_charts

    keywords_filter = set(keywords_filter)
    name_filter = name_filter
    platforms = False
    assert (
        settings.helm_extensions_cache is not None
    ), f"HELM_EXTENSIONS_CACHE is not defined"
    chart_tgz_files = [
        f
        for f in glob.glob(os.path.join(settings.helm_extensions_cache, "*.tgz"))
        if name_filter in f
    ]
    if "kaapanaplatform" in keywords_filter:
        assert (
            settings.helm_platforms_cache is not None
        ), f"HELM_PLATFORMS_CACHE is not defined"
        platforms = True
        current_hash = global_charts_hashes_platforms
        current_tgz_charts = global_collected_tgz_charts_platforms
        chart_tgz_files += [
            f
            for f in glob.glob(os.path.join(settings.helm_platforms_cache, "*.tgz"))
            if name_filter in f
        ]
    logger.info(f"found chart tgz files length: {len(chart_tgz_files)}")
    logger.debug(f"found chart tgz files: {chart_tgz_files}")
    collected_tgz_charts: dict = {}
    for chart_tgz_file in chart_tgz_files:
        chart_hash = sha256sum(filepath=chart_tgz_file)
        if (
            chart_tgz_file not in current_hash
            or chart_hash != current_hash[chart_tgz_file]
        ):
            logger.info(
                f"Chart {basename(chart_tgz_file)} has been modified -> reading tgz!"
            )

            helm_command = f"{settings.helm_path} show chart {chart_tgz_file}"
            success, stdout = execute_shell_command(helm_command)
            if success:
                current_hash[chart_tgz_file] = chart_hash

                logger.debug(f"Loading chart yaml in dict ...")
                chart = list(yaml.load_all(stdout, yaml.FullLoader))[0]
                if "keywords" in chart and (set(chart["keywords"]) & keywords_filter):
                    logger.debug(f"Valid keyword-filter!")
                    vals = helm_show_values(
                        chart["name"], chart["version"], platforms=platforms
                    )
                    if (vals is not None) and "extension_params" in vals:
                        chart = add_extension_params(chart, vals)
                    if (vals is not None) and "links" in vals["global"]:
                        logger.debug(
                            f"'links' specified in values.yaml of {chart['name']}"
                        )
                        chart["links"] = vals["global"]["links"]
                    current_tgz_charts[f'{chart["name"]}-{chart["version"]}'] = chart
                    collected_tgz_charts[f'{chart["name"]}-{chart["version"]}'] = chart
                else:
                    logger.debug(f"skipping due to keyword-filter - {keywords_filter=}")
            else:
                logger.error(f"execution not successful!")
        else:
            logger.debug(f"scraping not necessary!")

    # file is deleted, remove from hashes and global_collected_tgz_charts
    # TODO: this is messy, handle this in an endpoint like (/file-delete)
    set_files = set(chart_tgz_files)
    if name_filter == "" and len(current_hash) > len(set_files):
        hash_keys = set(current_hash.keys())
        diff = hash_keys.difference(set_files)
        logger.info(
            f"File(s) removed from the folder, {hash_keys=}, {set_files=}, {diff=}"
        )
        for f in diff:
            logger.info(f"Deleting hash and chart info for file {f}")
            current_hash.pop(f)
            fname = ".".join(f.split("/")[-1].split(".")[:-1])
            current_tgz_charts.pop(fname)

    #logger.debug(f"{current_tgz_charts=}")
    if name_filter != "":
        if len(collected_tgz_charts) > 0:
            logger.debug(f"returning {collected_tgz_charts=}")
            return collected_tgz_charts

        if name_filter in current_tgz_charts:
            chart_dict = {name_filter: current_tgz_charts[name_filter]}
            logger.debug(f"returning {chart_dict}")
            return chart_dict

    if "kaapanaplatform" in keywords_filter:
        global_charts_hashes_platforms = current_hash
        global_collected_tgz_charts_platforms = current_tgz_charts
    else:
        global_charts_hashes = current_hash
        global_collected_tgz_charts = current_tgz_charts

    return current_tgz_charts


def sha256sum(filepath) -> str:
    # logger.debug(f"In method: sha256sum({filepath=})")
    h = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filepath, "rb", buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])

    # logger.debug(f"End method: sha256sum({filepath=})")
    return h.hexdigest()


def collect_helm_deployments(
    helm_namespace: str = settings.helm_namespace,
    chart_name: str = None,
    platforms: bool = False,
) -> Dict[str, Dict]:
    """
    Gets all deployed helm charts independent of their status

    Arguments:
        helm_namespace (str): Namespace for helm commands
        chart_name (str): If not None only return charts with matched name

    Returns:
        deployed_charts_dict (Dict[str, Dict]): format for keys is `chart['chart']`

    """
    deployed_charts_dict = {}
    namespace_option = f"-n {helm_namespace}"
    if platforms:
        namespace_option = "-A"
    cmd = f"{settings.helm_path} ls {namespace_option} --deployed --pending --failed --uninstalling --superseded -o json"
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


def get_kube_objects(
    release_name: str,
    helm_namespace: str = settings.helm_namespace,
    single_status_for_jobs: bool = False,
) -> Tuple[bool, bool, List[str], schemas.KubeInfo]:
    """
    Gets information about all kube objects in helm manifest

    Arguments:
        release_name           (str) : Name of the helm chart
        helm_namespace         (str) : Namespace for helm commands
        single_status_for_jobs (bool): Whether to return a single status for jobs if there are many pods but at least one is completed

    Returns:
        success             (bool)             : whether the helm command ran successfully
        deployment_ready    (bool)             : whether all kube objects are in "Running" or "Completed" states
        paths       (List[str])        : paths extracted from ingress and service objects
        concatenated_states (schemas.KubeInfo]): contains all information about related kube objects
    """

    def get_pod_status(
        kind, name, namespace, single_status_for_jobs: bool = False
    ) -> Union[schemas.KubeInfo, None]:
        """
        Returns pod information as KubeInfo
        """
        states = None
        # TODO: might be replaced by json or yaml output in the future with the flag -o json!
        if kind == "job":
            pod_label = "batch.kubernetes.io/job-name"
        elif kind == "app":
            pod_label = "app.kubernetes.io/name"
        else:
            logger.error(f"Unknown kind: {kind}. Must be one of ['job', 'app'].")
            raise ValueError(f"Unknown kind: {kind}. Must be one of ['job', 'app'].")

        success, stdout = execute_shell_command(
            f"{settings.kubectl_path} -n {namespace} get pod -l={pod_label}={name}"
        )
        if success:
            states = schemas.KubeInfo(
                name=[], ready=[], status=[], restarts=[], age=[], annotations={}
            )

            stdout = stdout.splitlines()[1:]

            # for pods of a Job, check if one of them already has 'completed' status
            job_completed = False
            if kind == "job" and single_status_for_jobs:
                for row in stdout:
                    name, ready, status, restarts, age = re.split(r"\s\s+", row)
                    if status.lower() == "completed":
                        # ignore other pods and only return the completed pod status
                        job_completed = True
                        logger.info(
                            f"job {name=} has a completed pod, ignoring its other pods"
                        )
                        states.name = [name]
                        states.ready = [ready]
                        states.status = [status.lower()]
                        states.restarts = [restarts]
                        states.age = [age]
                        break

            if not job_completed:
                # return all pod states if no pod is completed or if resource kind is not Job
                for row in stdout:
                    name, ready, status, restarts, age = re.split(r"\s\s+", row)
                    states.name.append(name)
                    states.ready.append(ready)
                    states.status.append(status.lower())
                    states.restarts.append(restarts)
                    states.age.append(age)
        else:
            logger.error(f"Could not get kube status of {name}")
            logger.error(stdout)

        return states

    logger.debug(f"get_kube_objects for ({release_name=}, {helm_namespace=})")
    success, stdout = execute_shell_command(
        f"{settings.helm_path} -n {helm_namespace} get manifest {release_name}"
    )
    paths = []
    concatenated_states = schemas.KubeInfo(
        name=[], ready=[], status=[], restarts=[], age=[], annotations={}
    )
    if success:
        manifest_dict = list(yaml.load_all(stdout, yaml.FullLoader))
        deployment_ready = True
        # convert configs inside chart's manifest to concatenated KubeInfo
        for config in manifest_dict:
            logger.debug(config)
            if config is None:
                continue

            # collect annotations from every k8s resource that matches any of the patterns
            annotation_keys_include_patterns = ["*/kaapana.ai/*"]
            annotations = config.get("metadata", {}).get("annotations", {})
            for key, value in annotations.items():
                if any(
                    fnmatch.fnmatch(key, pattern)
                    for pattern in annotation_keys_include_patterns
                ):
                    if key not in concatenated_states.annotations:
                        concatenated_states.annotations[key] = value

            # based on the kind of resource, extract relevant information
            kind = config["kind"]
            if kind == "Ingress":
                path = config["spec"]["rules"][0]["http"]["paths"][0]["path"]
                paths.append(path)
            elif (
                kind == "Service"
                and "type" in config["spec"]
                and config["spec"]["type"] == "NodePort"
            ):
                if "nodePort" not in config["spec"]["ports"][0]:
                    continue
                nodeport = config["spec"]["ports"][0]["nodePort"]
                nodeport_path = ":" + str(nodeport)
                paths.append(nodeport_path)
            elif kind == "Deployment" or kind == "Job":
                obj_kube_status = None
                if kind == "Deployment":
                    # TODO: only traefik lacks app.kubernetes.io/name in matchLabels
                    match_labels = config["spec"]["selector"]["matchLabels"]
                    app_name = match_labels.get("app.kubernetes.io/name")
                    if not app_name:
                        app_name = "-- UNKNOWN APP --"
                    obj_kube_status = get_pod_status(
                        "app", app_name, config["metadata"]["namespace"]
                    )
                elif kind == "Job":
                    obj_kube_status = get_pod_status(
                        "job",
                        config["metadata"]["name"],
                        config["metadata"]["namespace"],
                        single_status_for_jobs,
                    )

                if obj_kube_status != None:
                    for key, value in obj_kube_status.dict().items():
                        if key == "annotations":
                            concatenated_states[key].update(value)
                        else:
                            concatenated_states[key].extend(value)

                        if (
                            key == "status"
                            and value[0] != KUBE_STATUS_COMPLETED
                            and value[0] != KUBE_STATUS_RUNNING
                        ):
                            deployment_ready = False
    else:
        logger.error(f"Error fetching kube-objects: {release_name=}")
        deployment_ready = False

    return success, deployment_ready, paths, concatenated_states


def helm_show_values(name, version, platforms=False) -> Dict:
    """
    Returns result of 'helm show values' for tgz file
    """
    helm_cache_dir = settings.helm_extensions_cache
    if platforms:
        assert (
            settings.helm_platforms_cache is not None
        ), f"HELM_PLATFORMS_CACHE is not defined"
        helm_cache_dir = settings.helm_platforms_cache

        curr_fpath = f"{helm_cache_dir}/{name}-{version}.tgz"
        if not os.path.exists(curr_fpath):
            helm_cache_dir = settings.helm_extensions_cache
    success, stdout = execute_shell_command(
        f"{settings.helm_path} show values {helm_cache_dir}/{name}-{version}.tgz"
    )
    if success:
        return list(yaml.load_all(stdout, yaml.FullLoader))[0]
    else:
        return {}


def helm_show_chart(name=None, version=None, package=None, platforms=False) -> Dict:
    """
    Returns result of 'helm show chart' for package, if it is availabe. Otherwise runs for the tgz file
    """
    helm_command = f"{settings.helm_path} show chart"

    if package is not None:
        helm_command = f"{helm_command} {package}"
    else:
        helm_cache_dir = settings.helm_extensions_cache
        if platforms:
            assert (
                settings.helm_platforms_cache is not None
            ), f"HELM_PLATFORMS_CACHE is not defined"
            helm_cache_dir = settings.helm_platforms_cache

            curr_fpath = f"{helm_cache_dir}/{name}-{version}.tgz"
            if not os.path.exists(curr_fpath):
                helm_cache_dir = settings.helm_extensions_cache
        helm_command = f"{helm_command} {helm_cache_dir}/{name}-{version}.tgz"

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
        for ext in global_extensions_list:
            for v in ext["available_versions"]:
                state = schemas.ExtensionStateType.NOT_INSTALLED
                if len(ext["available_versions"][v]["deployments"]) > 0:
                    state = schemas.ExtensionStateType.INSTALLED

                key = ext["chart_name"] + "__" + v
                global_extension_states[key] = schemas.ExtensionState.construct(
                    extension_name=ext.chart_name,
                    extension_version=v,
                    releaseName=ext.releaseName,
                    state=state,
                    update_time=time.time(),
                    last_read_time=time.time(),
                    recently_updated=False,  # since it's the initialization,
                    multiinstallable=(
                        True if ext["multiinstallable"] == "yes" else False
                    ),
                )
        return

    if state is None:
        logger.error("update_extension_state got an empty state object")
        return

    name = state["extension_name"]
    version = state["extension_version"]
    key = name + "__" + version
    if key not in global_extension_states:
        logger.warning(
            f"{key} is not already in global_extension_states, adding a new entry"
        )
        global_extension_states[key] = schemas.ExtensionState.construct(
            extension_name=name,
            extension_version=version,
            releaseName=name,
            state=state.state,
            update_time=time.time(),
            last_read_time=time.time(),
            recently_updated=True,
            multiinstallable=state.multiinstallable,
        )
    else:
        logger.debug(f"{key} is already in global_extension_states, updating")
        ext = global_extension_states[key]
        logger.debug(f"before update {ext}")
        prev_state = ext.state
        logger.info(f"updating extension state to {state.state} from {prev_state}")
        ext.update_time = time.time()
        ext.last_read_time = time.time()
        ext.recently_updated = True
        logger.debug(f"after update {ext}")
    global_recently_updated.add(key)


def get_recently_updated_extensions() -> List[schemas.KaapanaExtension]:
    """
    get states for keys in recently_updated set
    """
    global global_extension_states, global_recently_updated, global_extensions_list
    res: List[Tuple[int, schemas.KaapanaExtension]] = []
    to_remove = []
    logger.debug(
        f"get_recently_updated_extensions called with {global_recently_updated=}"
    )
    for key in global_recently_updated:
        ext_state = global_extension_states[key]
        for i, ext in enumerate(global_extensions_list):
            if ext.releaseName == ext_state.extension_name:
                res.append((i, global_extensions_list[i]))
        logger.debug(f"{res=}")
        if len(res) > 1:
            logger.error(
                f"Found more than one matching charts for {ext_state.extension_name} in cached extensions dict"
            )
        elif len(res) == 0:
            # found new chart
            logger.info(f"New chart {ext_state.extension_name}")
            fname, version = key.split("__")
            name = "-".join(fname[:-4].split("-")[0:-1])
            res.append(
                (
                    len(global_extensions_list),
                    schemas.KaapanaExtension.construct(
                        releaseName=ext_state.releaseName,
                        multiinstallable=(
                            "yes" if ext_state.multiinstallable == True else "no"
                        ),
                        chart_name=name,
                        version=version,
                    ),
                )
            )
            to_remove.append(key)

        ext_state.last_read_time = time.time()
        # if not longer recent, update its state and remove from set
        if ext_state["last_read_time"] - ext_state["update_time"] > REFRESH_DELAY:
            ext_state.recently_updated = False
            to_remove.append(key)

    # remove the ones that are not recently updated anymore
    for k in to_remove:
        if k in global_recently_updated:
            global_recently_updated.remove(k)

    return res


def add_extension_params(chart, vals):
    """
    Add 'extension_params' from vals to chart object.
    """
    logger.debug(f"in function add_extension_params {chart['name']=}")
    # TODO: validate the parameter fields
    params_dict = vals["extension_params"]
    logger.debug(f"extension_params {params_dict}")
    chart["extension_params"] = params_dict
    return chart
