#!/usr/bin/env python3
from shutil import which, copy, rmtree
import yaml
import os
import logging
from os.path import join, dirname, basename, exists, isfile, isdir
from time import time
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from argparse import ArgumentParser
from build_helper.charts_helper import HelmChart, init_helm_charts, helm_registry_login
from build_helper.container_helper import Container, container_registry_login
from build_helper.build_utils import BuildUtils

build_dir = join(dirname(dirname(os.path.realpath(__file__))), "build")
if exists(build_dir):
    rmtree(build_dir)
os.makedirs(build_dir, exist_ok=True)

# Create a custom logger
logging.getLogger().setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)

c_handler = logging.StreamHandler()
c_handler.setLevel(logging.DEBUG)

f_handler = logging.FileHandler(join(build_dir, "build.log"))
f_handler.setLevel(logging.DEBUG)

c_format = logging.Formatter('%(levelname)s - %(message)s')
f_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
c_handler.setFormatter(c_format)
f_handler.setFormatter(f_format)

# Add handlers to the logger
logger.addHandler(c_handler)
logger.addHandler(f_handler)

supported_log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]

terminal_width = int(os.get_terminal_size()[0] * 0.5)
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument("-c", "--config", dest="config_filepath", default=None, help="Path the the build-configuration.yaml")
    parser.add_argument("-u", "--username", dest="username", default=None, help="Username")
    parser.add_argument("-p", "--password", dest="password", default=None, required=False, help="Password")
    parser.add_argument("-bo", "--build-only", dest="build_only", default=None, action='store_true', help="Just building the containers and charts -> no pushing")
    parser.add_argument("-oi", "--create-offline-installation", dest="create_offline_installation", default=None, help="Will create a docker dump, from which the platfrom can be installed.")
    parser.add_argument("-pm", "--push-to-microk8s", dest="push_to_microk8s", default=None, help="Will create a docker dump, from which the platfrom can be installed.")
    parser.add_argument("-kd", "--kaapana-dir", dest="kaapaa_dir", default=None, help="Kaapana repo path.")
    parser.add_argument("-ll", "--log-level", dest="log_level", default=None, help="Set log-level.")
    parser.add_argument("-el", "--enable-linting", dest="enable_linting", default=None, help="Enable Helm Chart lint & kubeval.")
    parser.add_argument("-sp", "--skip-push-no-changes", dest="skip_push_no_changes", default=None, help="Skip the image push if it didn't change.")
    parser.add_argument("-ee", "--exit-on-error", dest="exit_on_error", default=None, help="Stop build-process if error occurs.")
    parser.add_argument("-pf", "--plartform-filter", dest="platform_filter", default=None, help="Specify platform-chart-names to be build (comma seperated).")
    parser.add_argument("-es", "--external-sources", dest="external_source_dirs", default=None, help="External dirs to search for containers and charts.")
    args = parser.parse_args()

    kaapana_dir = args.kaapaa_dir if args.kaapaa_dir != None else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if not os.path.isdir(os.path.join(kaapana_dir, "platforms")):
        logger.error("-----------------------------------------------------------")
        logger.error("The dir 'platforms' was not found! -> wrong kaapana_dir? -> exit!")
        logger.error("-----------------------------------------------------------")
        exit(1)

    config_filepath = args.config_filepath
    config_filepath = config_filepath if config_filepath is not None else os.path.join(kaapana_dir, "build-scripts", "build-configuration.yaml")
    if not os.path.isfile(config_filepath):
        logger.error(f"The build-configuration.yaml file was not found at: {config_filepath}")
        logger.error("-----------------------------------------------------------")
        exit(1)
    logger.info("-----------------------------------------------------------")
    logger.info("--------------- loading build-configuration ---------------")
    logger.info("-----------------------------------------------------------")

    with open(config_filepath, 'r') as stream:
        try:
            configuration = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.info(exc)

    conf_http_proxy = configuration["http_proxy"]
    conf_default_registry = configuration["default_registry"]
    conf_container_engine = configuration["container_engine"]
    conf_log_level = configuration["log_level"]
    conf_build_only = configuration["build_only"]
    conf_create_offline_installation = configuration["create_offline_installation"]
    conf_push_to_microk8s = configuration["push_to_microk8s"]
    conf_platform_filter = configuration["platform_filter"].split(",") if configuration["platform_filter"].replace(" ", "") != "" else []
    conf_external_source_dirs = configuration["external_source_dirs"].split(",") if configuration["external_source_dirs"].replace(" ", "") != "" else []
    conf_exit_on_error = configuration["exit_on_error"]
    conf_enable_linting = configuration["enable_linting"]
    conf_enable_build_kit = 1 if "enable_build_kit" in configuration and configuration["enable_build_kit"] else 0
    conf_skip_push_no_changes = configuration["skip_push_no_changes"]

    registry_user = args.username
    registry_pwd = args.password

    build_only = args.build_only if args.build_only != None else conf_build_only
    create_offline_installation = args.create_offline_installation if args.create_offline_installation != None else conf_create_offline_installation
    push_to_microk8s = args.push_to_microk8s if args.push_to_microk8s != None else conf_push_to_microk8s
    external_source_dirs = args.external_source_dirs.split(",") if args.external_source_dirs != None else conf_external_source_dirs
    log_level = args.log_level if args.log_level != None else conf_log_level
    enable_linting = args.enable_linting if args.enable_linting != None else conf_enable_linting
    exit_on_error = args.exit_on_error if args.exit_on_error != None else conf_exit_on_error
    platform_filter = args.platform_filter.split(",") if args.platform_filter != None else conf_platform_filter
    skip_push_no_changes = args.skip_push_no_changes if args.skip_push_no_changes != None else conf_skip_push_no_changes

    for external_source_dir in external_source_dirs:
        if not os.path.isdir(external_source_dir):
            logger.error("-----------------------------------------------------------")
            logger.error(f"External source-dir: {external_source_dir} does not exist -> exit!")
            logger.error("-----------------------------------------------------------")
            exit(1)

    charts_lint = True if enable_linting else False
    charts_kubeval = True if enable_linting else False
    charts_push = False if build_only else True
    containers_push = False if build_only else True
    container_build = True
    build_installer_scripts = True

    container_engine = "docker" if "container_engine" not in configuration else configuration["container_engine"]
    default_registry = configuration["default_registry"] if "default_registry" in configuration else ""

    http_proxy = conf_http_proxy if conf_http_proxy != "" else None
    http_proxy = os.environ.get("http_proxy", "") if http_proxy == None and os.environ.get("http_proxy", None) != None else None

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info("                       BUILD CONFIG                        ")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info(f"{http_proxy=}")
    logger.info(f"{build_only=}")
    logger.info(f"{create_offline_installation=}")
    logger.info(f"{external_source_dirs=}")
    logger.info(f"{log_level=}")
    logger.info(f"{enable_linting=}")
    logger.info(f"{exit_on_error=}")
    logger.info(f"{platform_filter=}")
    logger.info(f"{charts_kubeval=}")
    logger.info(f"{charts_kubeval=}")
    logger.info(f"{charts_push=}")
    logger.info(f"{container_build=}")
    logger.info(f"{containers_push=}")
    logger.info(f"{push_to_microk8s=}")
    logger.info(f"{build_installer_scripts=}")
    logger.info(f"{container_engine=}")
    logger.info(f"{default_registry=}")
    logger.info(f"{skip_push_no_changes=}")
    logger.info("")
    logger.info("-----------------------------------------------------------")

    if not build_only:
        if registry_user is None:
            registry_user = os.getenv("REGISTRY_USER", None)
        if registry_pwd is None:
            registry_pwd = os.getenv("REGISTRY_PW", None)

        if registry_user == None or registry_pwd == None:
            logger.error("REGISTRY CREDENTIALS ERROR:")
            logger.error(f"{build_only=} -> registry_user == None or registry_pwd == None")
            logger.error("You have to either specify --username & --password ")
            logger.error("Or use the ENVs: 'REGISTRY_USER' & 'REGISTRY_PW' !")
            exit(1)

    if log_level not in supported_log_levels:
        logger.error(f"Log level {log_level} not supported.")
        logger.error("Please use 'DEBUG','WARN' or 'ERROR' for log_level in build-configuration.json")
        exit(1)

    logger.debug(f"LOG-LEVEL: {log_level}")

    if log_level == "DEBUG":
        c_handler.setLevel(logging.DEBUG)
    elif log_level == "INFO":
        c_handler.setLevel(logging.INFO)
    elif log_level == "WARN":
        c_handler.setLevel(logging.WARNING)
    elif log_level == "ERROR":
        c_handler.setLevel(logging.ERROR)
    else:
        logger.error(f"Log level {log_level} not identified!")
        exit(1)

    log_level_int = supported_log_levels.index(log_level)

    BuildUtils.init(
        kaapana_dir=kaapana_dir,
        build_dir=build_dir,
        external_source_dirs=external_source_dirs,
        platform_filter=platform_filter,
        default_registry=default_registry,
        http_proxy=http_proxy,
        exit_on_error=exit_on_error,
        logger=logger,
        enable_build_kit=conf_enable_build_kit,
        create_offline_installation=create_offline_installation,
        skip_push_no_changes=skip_push_no_changes,
        push_to_microk8s=push_to_microk8s
    )

    Container.init_containers(
        container_engine=container_engine,
        enable_build=container_build,
        enable_push=containers_push,
    )
    if not build_only:
        container_registry_login(username=registry_user, password=registry_pwd)
        helm_registry_login(username=registry_user, password=registry_pwd)

    container_images_available = Container.collect_containers()
    BuildUtils.add_container_images_available(container_images_available=container_images_available)
    charts_available = HelmChart.collect_charts()

    init_helm_charts(
        save_tree=True,
        enable_push=charts_push,
        enable_lint=charts_lint,
        enable_kubeval=charts_kubeval,
    )

    startTime = time()
    if build_installer_scripts:
        logger.info("-----------------------------------------------------------")
        logger.info("-------------------- Installer scripts --------------------")
        logger.info("-----------------------------------------------------------")
        platforms_dir = Path(kaapana_dir) / "platforms"
        logger.info(str(platforms_dir))
        file_loader = FileSystemLoader(str(platforms_dir))  # directory of template file
        env = Environment(loader=file_loader)
        for config_path in platforms_dir.rglob('installer_config.yaml'):
            platform_params = yaml.load(open(config_path), Loader=yaml.FullLoader)
            logger.info(f'# Creating installer script for {platform_params["project_name"]}')
            template = env.get_template('install_platform_template.sh')  # load template file

            output = template.render(**platform_params)
            with open(config_path.parents[0] / 'install_platform.sh', 'w') as rsh:
                rsh.write(output)

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD PLATFORM CHARTS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")

    HelmChart.generate_platform_build_tree()

    if len(BuildUtils.issues_list) > 0:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------------ ISSUES: --------------------------")
        logger.info("-----------------------------------------------------------")
        for issue in BuildUtils.issues_list:
            component = issue["component"]
            name = issue["name"]
            level = issue["level"]
            log = issue["log"]
            msg = issue["msg"]
            timestamp = issue["timestamp"]
            filepath = issue["filepath"]
            logger.warning("")
            logger.warning(f"{level} -> {component}:{name}")
            logger.warning(f"{msg=}")
            logger.warning(log)
            logger.warning("")
            logger.warning("-----------------------------------------------------------")

    hours, rem = divmod(time()-startTime, 3600)
    minutes, seconds = divmod(rem, 60)
    logger.info("")
    logger.info("")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ TIME NEEDED: {:0>2}:{:0>2}:{:0>2} -----------------".format(int(hours), int(minutes), int(seconds)))
    logger.info("-----------------------------------------------------------")
    logger.info("-------------------------- DONE ---------------------------")
    logger.info("-----------------------------------------------------------")
