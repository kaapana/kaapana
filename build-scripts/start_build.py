#!/usr/bin/env python3
from shutil import copyfile, rmtree
import yaml
import os
import logging
from os.path import join, dirname, basename, exists, isfile, isdir
from time import time
from argparse import ArgumentParser
from build_helper.charts_helper import HelmChart, init_helm_charts, helm_registry_login
from build_helper.container_helper import Container, container_registry_login
from build_helper.build_utils import BuildUtils
from build_helper.security_utils import TrivyUtils


supported_log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument(
        "-c",
        "--config",
        dest="config_filepath",
        default=None,
        help="Path the the build-config.yaml",
    )
    parser.add_argument(
        "-u", "--username", dest="username", default=None, help="Username"
    )
    parser.add_argument(
        "-p",
        "--password",
        dest="password",
        default=None,
        required=False,
        help="Password",
    )
    parser.add_argument(
        "-dr",
        "--default-registry",
        dest="default_registry",
        default=None,
        help="Name of the registry to which the platform should be build.",
    )
    parser.add_argument(
        "-bo",
        "--build-only",
        dest="build_only",
        default=None,
        action="store_true",
        help="Just building the containers and charts -> no pushing",
    )
    parser.add_argument(
        "-oi",
        "--create-offline-installation",
        dest="create_offline_installation",
        action="store_true",
        default=None,
        help="Will create a docker dump, from which the platfrom can be installed.",
    )
    parser.add_argument(
        "-pm",
        "--push-to-microk8s",
        dest="push_to_microk8s",
        default=None,
        help="Will create a docker dump, from which the platfrom can be installed.",
    )
    parser.add_argument(
        "-kd",
        "--kaapana-dir",
        dest="kaapana_dir",
        default=None,
        help="Kaapana repo path.",
    )
    parser.add_argument(
        "-ll", "--log-level", dest="log_level", default=None, help="Set log-level."
    )
    parser.add_argument(
        "-el",
        "--enable-linting",
        dest="enable_linting",
        action="store_true",
        default=None,
        help="Enable Helm Chart lint & kubeval.",
    )
    parser.add_argument(
        "-sp",
        "--skip-push-no-changes",
        dest="skip_push_no_changes",
        default=None,
        action="store_true",
        help="Skip the image push if it didn't change.",
    )
    parser.add_argument(
        "-ee",
        "--exit-on-error",
        dest="exit_on_error",
        default=None,
        action="store_true",
        help="Stop build-process if error occurs.",
    )
    parser.add_argument(
        "-pf",
        "--plartform-filter",
        dest="platform_filter",
        default=None,
        help="Specify platform-chart-names to be build (comma seperated).",
    )
    parser.add_argument(
        "-es",
        "--external-sources",
        dest="external_source_dirs",
        default=None,
        help="External dirs to search for containers and charts.",
    )
    parser.add_argument(
        "-pp",
        "--parallel-processes",
        dest="parallel_processes",
        default=2,
        help="Parallel process count for container build + push.",
    )
    parser.add_argument(
        "-ic",
        "--include-credentials",
        dest="include_credentials",
        default=None,
        action="store_true",
        help="Whether to inlude the used registry credentials into the deploy-platform script.",
    )
    parser.add_argument(
        "-bd",
        "--build-dir",
        dest="build_dir",
        default=None,
        help="Specify the main Kaapana repo-dir to build from.",
    )
    parser.add_argument(
        "-bip",
        "--build-ignore-patterns",
        dest="build_ignore_patterns",
        default=None,
        help="Comma seperated list of directory paths or files that should be ignored.",
    )
    parser.add_argument(
        "-nl",
        "--no-login",
        dest="no_login",
        default=False,
        action="store_true",
        help="Skipps the logins to the container registry (expects to be already logged in).",
    )
    parser.add_argument(
        "-vs",
        "--vulnerability-scan",
        dest="vulnerability_scan",
        default=None,
        action="store_true",
        help="Scan the built containers with trivy for vulnerabilities.",
    )
    parser.add_argument(
        "-vsl",
        "--vulnerability-severity-level",
        dest="vulnerability_severity_level",
        default=None,
        action="store_true",
        help="Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN.",
    )
    parser.add_argument(
        "-cc",
        "--configuration-check",
        dest="configuration_check",
        default=None,
        action="store_true",
        help="Wheter the Charts, deployments, dockerfiles etc. should be checked for configuration errors",
    )
    parser.add_argument(
        "-ccl",
        "--configuration-check-severity-level",
        dest="configuration_check_severity_level",
        default=None,
        action="store_true",
        help="Filter by severity of findings. CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN.",
    )
    parser.add_argument(
        "-is",
        "--enable-image-stats",
        dest="enable_image_stats",
        default=None,
        action="store_true",
        help="Enable container image size statistics (image_stats.json)",
    )
    parser.add_argument(
        "--latest",
        dest="latest",
        default=False,
        action="store_true",
        help="Force version to 'latest'",
    )
    args = parser.parse_args()

    kaapana_dir = (
        args.kaapana_dir
        if args.kaapana_dir != None
        else os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    build_dir = (
        args.build_dir
        if args.build_dir != None
        else join(dirname(dirname(os.path.realpath(__file__))), "build")
    )

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

    c_format = logging.Formatter("%(levelname)s - %(message)s")
    f_format = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    # Add handlers to the logger
    logger.addHandler(c_handler)
    logger.addHandler(f_handler)

    if not os.path.isdir(os.path.join(kaapana_dir, "platforms")):
        logger.error(
            "----------------------------------------------------------------------"
        )
        logger.error(
            "The dir 'platforms' was not found! -> wrong kaapana_dir? -> exit!"
        )
        logger.error(
            "----------------------------------------------------------------------"
        )
        exit(1)

    template_config_filepath = os.path.join(
        kaapana_dir, "build-scripts", "build-config-template.yaml"
    )
    assert exists(template_config_filepath)
    with open(template_config_filepath, "r") as stream:
        try:
            template_configuration = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.info(exc)

    config_filepath = args.config_filepath
    config_filepath = (
        config_filepath
        if config_filepath is not None
        else os.path.join(kaapana_dir, "build-scripts", "build-config.yaml")
    )
    template_config_filepath = os.path.join(
        kaapana_dir, "build-scripts", "build-config-template.yaml"
    )
    if not os.path.isfile(config_filepath):
        logger.error("")
        logger.error("")
        logger.error(f"The build-configuration.yaml was not found!")
        logger.error(f"Default config has been created -> please adjust as needed !!")
        logger.error("")
        logger.error(f"See: {config_filepath}")
        copyfile(src=template_config_filepath, dst=config_filepath)
        logger.error("")
        logger.error("")
        logger.error("-----------------------------------------------------------")
        exit(1)
    logger.info("-----------------------------------------------------------")
    logger.info("--------------- loading build-configuration ---------------")
    logger.info("-----------------------------------------------------------")

    with open(config_filepath, "r") as stream:
        try:
            configuration = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            logger.info(exc)

    conf_http_proxy = (
        configuration["http_proxy"]
        if "http_proxy" in configuration
        else template_configuration["http_proxy"]
    )
    conf_default_registry = (
        configuration["default_registry"]
        if "default_registry" in configuration
        else template_configuration["default_registry"]
    )
    conf_container_engine = (
        configuration["container_engine"]
        if "container_engine" in configuration
        else template_configuration["container_engine"]
    )
    conf_log_level = (
        configuration["log_level"]
        if "log_level" in configuration
        else template_configuration["log_level"]
    )
    conf_build_only = (
        configuration["build_only"]
        if "build_only" in configuration
        else template_configuration["build_only"]
    )
    conf_create_offline_installation = (
        configuration["create_offline_installation"]
        if "create_offline_installation" in configuration
        else template_configuration["create_offline_installation"]
    )
    conf_push_to_microk8s = (
        configuration["push_to_microk8s"]
        if "push_to_microk8s" in configuration
        else template_configuration["push_to_microk8s"]
    )
    conf_platform_filter = (
        configuration["platform_filter"].split(",")
        if configuration["platform_filter"].replace(" ", "") != ""
        else []
    )
    conf_external_source_dirs = (
        configuration["external_source_dirs"].split(",")
        if configuration["external_source_dirs"].replace(" ", "") != ""
        else []
    )
    conf_build_ignore_patterns = (
        configuration["build_ignore_patterns"].split(",")
        if configuration["build_ignore_patterns"].replace(" ", "") != ""
        else []
    )
    conf_exit_on_error = (
        configuration["exit_on_error"]
        if "exit_on_error" in configuration
        else template_configuration["exit_on_error"]
    )
    conf_enable_linting = (
        configuration["enable_linting"]
        if "enable_linting" in configuration
        else template_configuration["enable_linting"]
    )
    conf_enable_build_kit = (
        1
        if "enable_build_kit" in configuration and configuration["enable_build_kit"]
        else 0
    )
    conf_skip_push_no_changes = (
        configuration["skip_push_no_changes"]
        if "skip_push_no_changes" in configuration
        else template_configuration["skip_push_no_changes"]
    )
    conf_parallel_processes = (
        configuration["parallel_processes"]
        if "parallel_processes" in configuration
        else template_configuration["parallel_processes"]
    )
    conf_registry_username = (
        configuration["registry_username"]
        if "registry_username" in configuration
        else template_configuration["registry_username"]
    )
    conf_registry_username = (
        conf_registry_username if conf_registry_username != "" else None
    )
    conf_registry_password = (
        configuration["registry_password"]
        if "registry_password" in configuration
        else template_configuration["registry_password"]
    )
    conf_registry_password = (
        conf_registry_password if conf_registry_password != "" else None
    )
    conf_include_credentials = (
        configuration["include_credentials"]
        if "include_credentials" in configuration
        else template_configuration["include_credentials"]
    )
    conf_vulnerability_scan = (
        configuration["vulnerability_scan"]
        if "vulnerability_scan" in configuration
        else template_configuration["vulnerability_scan"]
    )
    conf_vulnerability_severity_level = (
        configuration["vulnerability_severity_level"]
        if "vulnerability_severity_level" in configuration
        else template_configuration["vulnerability_severity_level"]
    )
    conf_configuration_check = (
        configuration["configuration_check"]
        if "configuration_check" in configuration
        else template_configuration["configuration_check"]
    )
    conf_configuration_check_severity_level = (
        configuration["configuration_check_severity_level"]
        if "configuration_check_severity_level" in configuration
        else template_configuration["configuration_check_severity_level"]
    )
    conf_enable_image_stats = (
        configuration["enable_image_stats"]
        if "enable_image_stats" in configuration
        else template_configuration["enable_image_stats"]
    )

    registry_user = (
        args.username if args.username is not None else conf_registry_username
    )
    registry_pwd = (
        args.password if args.password is not None else conf_registry_password
    )

    build_only = args.build_only if args.build_only != None else conf_build_only
    create_offline_installation = (
        args.create_offline_installation
        if args.create_offline_installation != None
        else conf_create_offline_installation
    )
    push_to_microk8s = (
        args.push_to_microk8s
        if args.push_to_microk8s != None
        else conf_push_to_microk8s
    )
    external_source_dirs = (
        args.external_source_dirs.split(",")
        if args.external_source_dirs != None
        else conf_external_source_dirs
    )
    build_ignore_patterns = (
        args.build_ignore_patterns.split(",")
        if args.build_ignore_patterns != None
        else conf_build_ignore_patterns
    )
    log_level = args.log_level if args.log_level != None else conf_log_level
    enable_linting = (
        args.enable_linting if args.enable_linting != None else conf_enable_linting
    )
    exit_on_error = (
        args.exit_on_error if args.exit_on_error != None else conf_exit_on_error
    )
    platform_filter = (
        args.platform_filter.split(",")
        if args.platform_filter != None
        else conf_platform_filter
    )
    skip_push_no_changes = (
        args.skip_push_no_changes
        if args.skip_push_no_changes != None
        else conf_skip_push_no_changes
    )
    parallel_processes = int(
        args.parallel_processes
        if args.parallel_processes != 2
        else conf_parallel_processes
    )
    include_credentials = (
        args.include_credentials
        if args.include_credentials != None
        else conf_include_credentials
    )
    vulnerability_scan = (
        args.vulnerability_scan
        if args.vulnerability_scan != None
        else conf_vulnerability_scan
    )
    vulnerability_severity_level = (
        args.vulnerability_severity_level
        if args.vulnerability_severity_level != None
        else conf_vulnerability_severity_level
    )
    configuration_check = (
        args.configuration_check
        if args.configuration_check != None
        else conf_configuration_check
    )
    configuration_check_severity_level = (
        args.configuration_check_severity_level
        if args.configuration_check_severity_level != None
        else conf_configuration_check_severity_level
    )
    enable_image_stats = (
        args.enable_image_stats
        if args.enable_image_stats != None
        else conf_enable_image_stats
    )
    no_login = args.no_login
    version_latest = args.latest

    for external_source_dir in external_source_dirs:
        if not os.path.isdir(external_source_dir):
            logger.error(
                "---------------------------------------------------------------------------------------------"
            )
            logger.error(
                f"External source-dir: {external_source_dir} does not exist -> exit!"
            )
            logger.error(
                "---------------------------------------------------------------------------------------------"
            )
            exit(1)

    charts_lint = True if enable_linting else False
    charts_kubeval = True if enable_linting else False
    charts_push = False if build_only else True
    containers_push = False if build_only else True
    container_build = True
    build_installer_scripts = True

    build_ignore_patterns = build_ignore_patterns + ["templates_and_examples/templates"]
    container_engine = (
        "docker"
        if "container_engine" not in configuration
        else configuration["container_engine"]
    )

    if args.default_registry is not None:
        default_registry = args.default_registry
    else:
        default_registry = (
            configuration["default_registry"]
            if "default_registry" in configuration
            else ""
        )

    http_proxy = conf_http_proxy if conf_http_proxy != "" else None
    http_proxy = (
        os.environ.get("http_proxy", "")
        if http_proxy == None and os.environ.get("http_proxy", None) != None
        else http_proxy
    )

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info("                       BUILD CONFIG                        ")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info(f"{http_proxy=}")
    logger.info(f"{platform_filter=}")
    logger.info(f"{external_source_dirs=}")
    logger.info(f"{build_ignore_patterns=}")
    logger.info(f"{default_registry=}")
    logger.info(f"{log_level=}")
    logger.info(f"{exit_on_error=}")
    logger.info(f"{container_engine=}")
    logger.info(f"{build_only=}")
    logger.info(f"{charts_lint=}")
    logger.info(f"{charts_kubeval=}")
    logger.info(f"{charts_push=}")
    logger.info(f"{enable_linting=}")
    logger.info(f"{containers_push=}")
    logger.info(f"{container_build=}")
    logger.info(f"{skip_push_no_changes=}")
    logger.info(f"{create_offline_installation=}")
    logger.info(f"{build_installer_scripts=}")
    logger.info(f"{push_to_microk8s=}")
    logger.info(f"{build_dir=}")
    logger.info(f"{kaapana_dir=}")
    logger.info(f"{no_login=}")
    logger.info(f"{version_latest=}")
    logger.info(f"{vulnerability_scan=}")
    logger.info(f"{vulnerability_severity_level=}")
    logger.info(f"{configuration_check=}")
    logger.info("")
    logger.info("-----------------------------------------------------------")

    if not build_only and not no_login:
        if registry_user is None:
            registry_user = os.getenv("REGISTRY_USER", None)
        if registry_pwd is None:
            registry_pwd = os.getenv("REGISTRY_PW", None)

        if registry_user == None or registry_pwd == None:
            logger.error("REGISTRY CREDENTIALS ERROR:")
            logger.error(
                f"{build_only=} -> registry_user == None or registry_pwd == None"
            )
            logger.error("You have to either specify --username & --password ")
            logger.error("Or use the ENVs: 'REGISTRY_USER' & 'REGISTRY_PW' !")
            exit(1)

    if log_level not in supported_log_levels:
        logger.error(f"Log level {log_level} not supported.")
        logger.error(
            "Please use 'DEBUG','WARN' or 'ERROR' for log_level in build-config.yaml"
        )
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

    BuildUtils.init()
    BuildUtils.kaapana_dir = kaapana_dir
    BuildUtils.build_dir = build_dir
    BuildUtils.external_source_dirs = external_source_dirs
    BuildUtils.build_ignore_patterns = build_ignore_patterns
    BuildUtils.platform_filter = platform_filter
    BuildUtils.default_registry = default_registry
    BuildUtils.http_proxy = http_proxy
    BuildUtils.exit_on_error = exit_on_error
    BuildUtils.logger = logger
    BuildUtils.enable_build_kit = conf_enable_build_kit
    BuildUtils.create_offline_installation = create_offline_installation
    BuildUtils.skip_push_no_changes = skip_push_no_changes
    BuildUtils.parallel_processes = parallel_processes
    BuildUtils.include_credentials = include_credentials
    BuildUtils.registry_user = registry_user
    BuildUtils.registry_pwd = registry_pwd
    BuildUtils.push_to_microk8s = push_to_microk8s
    BuildUtils.vulnerability_scan = vulnerability_scan
    BuildUtils.vulnerability_severity_level = vulnerability_severity_level
    BuildUtils.configuration_check = configuration_check
    BuildUtils.configuration_check_severity_level = configuration_check_severity_level
    BuildUtils.version_latest = version_latest
    BuildUtils.enable_image_stats = enable_image_stats

    Container.init_containers(
        container_engine=container_engine,
        enable_build=container_build,
        enable_push=containers_push,
    )

    if not build_only and not no_login:
        container_registry_login(username=registry_user, password=registry_pwd)
        helm_registry_login(username=registry_user, password=registry_pwd)

    container_images_available = Container.collect_containers()
    BuildUtils.add_container_images_available(
        container_images_available=container_images_available
    )
    charts_available = HelmChart.collect_charts()

    init_helm_charts(
        save_tree=True,
        enable_push=charts_push,
        enable_lint=charts_lint,
        enable_kubeval=charts_kubeval,
    )

    startTime = time()
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD PLATFORM CHARTS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")

    HelmChart.generate_platform_build_tree()

    # Check charts for configuation errors
    if BuildUtils.configuration_check:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ CHECK PLATFORM CHARTS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        for chart_object in BuildUtils.platform_filter:
            trivy_utils = TrivyUtils()
            trivy_utils.check_chart(
                path_to_chart=os.path.join(BuildUtils.build_dir, chart_object)
            )

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
            if len(log) > 0:
                for line_number, line in log.items():
                    if not line.isdigit():
                        logger.warning(line)
            logger.warning("")
            logger.warning(
                "-----------------------------------------------------------"
            )

    hours, rem = divmod(time() - startTime, 3600)
    minutes, seconds = divmod(rem, 60)
    logger.info("")
    logger.info("")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info(
        "------------------ TIME NEEDED: {:0>2}:{:0>2}:{:0>2} -----------------".format(
            int(hours), int(minutes), int(seconds)
        )
    )
    logger.info("-----------------------------------------------------------")
    logger.info("-------------------------- DONE ---------------------------")
    logger.info("-----------------------------------------------------------")
