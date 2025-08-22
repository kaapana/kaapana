import argparse
import os
import signal
import sys
from pathlib import Path
from shutil import copyfile, rmtree
from time import time

import yaml
from build_helper.build_config import BuildConfig
from build_helper.build_utils_v2 import BuildProgress, BuildUtils
from build_helper.charts_helper import (
    HelmChart,
    helm_registry_login,
    init_helm_charts,
    successful_built_containers,
)
from build_helper.container_helper_v2 import Container
from logger import CustomLogger


def apply_env_fallbacks(config: dict) -> dict:
    # Only set if not already set
    if not config.get("http_proxy"):
        config["http_proxy"] = os.getenv("http_proxy")

    if not config.get("registry_username"):
        config["registry_username"] = os.getenv("REGISTRY_USER")

    if not config.get("registry_password"):
        config["registry_password"] = os.getenv("REGISTRY_PW")

    return config


def load_yaml(path: Path) -> dict:
    """Loads YAML file content safely."""
    if not path.exists():
        return {}
    with path.open("r") as stream:
        return yaml.safe_load(stream) or {}


def merge_args_with_config(args: argparse.Namespace, config_data: dict) -> BuildConfig:
    """Merges CLI arguments with loaded YAML config using priority: args > config"""
    cli_dict = {k: v for k, v in vars(args).items() if v is not None}
    config_data.update(cli_dict)
    config_data = apply_env_fallbacks(config_data)
    return BuildConfig(**config_data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kaapana Platform Builder")
    parser.add_argument("--config", help="Path to build-config.yaml")
    parser.add_argument("--log-level", help="Log verbosity")
    parser.add_argument("--default-registry", help="Docker registry")
    parser.add_argument("--platform-filter", help="Comma-separated platform filter")
    parser.add_argument(
        "--external-source-dirs", help="Comma-separated external sources"
    )
    parser.add_argument(
        "--build-ignore-patterns", help="Comma-separated ignore patterns"
    )
    parser.add_argument("--username")
    parser.add_argument("--password")
    parser.add_argument("--build-only", action="store_true")
    parser.add_argument("--enable-linting", action="store_true")
    parser.add_argument("--exit-on-error", action="store_true")
    parser.add_argument("--push-to-microk8s")
    parser.add_argument("--create-offline-installation", action="store_true")
    parser.add_argument("--parallel-processes", type=int)
    parser.add_argument("--include-credentials", action="store_true")
    parser.add_argument("--vulnerability-scan", action="store_true")
    parser.add_argument("--vulnerability-severity-level")
    parser.add_argument("--configuration-check", action="store_true")
    parser.add_argument("--configuration-check-severity-level")
    parser.add_argument("--create-sboms", action="store_true")
    parser.add_argument("--enable-image-stats", action="store_true")
    parser.add_argument("--latest", dest="version_latest", action="store_true")
    parser.add_argument("--check-expired-vulnerabilities-database", action="store_true")
    parser.add_argument("--kaapana-dir")
    parser.add_argument("--build-dir")
    parser.add_argument("--no-login", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()

    script_dir = Path(__file__).resolve().parent.parent
    kaapana_dir = Path(args.kaapana_dir) if args.kaapana_dir else script_dir
    build_dir = Path(args.build_dir) if args.build_dir else kaapana_dir / "build"

    if build_dir.exists():
        rmtree(build_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    logger = CustomLogger(build_dir, initial_level="DEBUG").get_logger()

    config_path = (
        Path(args.config)
        if args.config
        else kaapana_dir / "build-scripts" / "build-config.yaml"
    )
    if not (kaapana_dir / "platforms").is_dir():
        logger.error(f"The directory `platforms` was not found in {kaapana_dir}.")
        exit(1)

    if not config_path.exists():
        logger.error("\nThe build-configuration.yaml was not found!")
        template_path = kaapana_dir / "build-scripts" / "build-config-template.yaml"
        assert template_path.exists()
        copyfile(src=template_path, dst=config_path)
        logger.error("Default config has been created -> please adjust as needed!!")
        logger.error(f"See: {config_path}\n")
        sys.exit(1)

    file_config = load_yaml(config_path)
    file_config.update(
        {
            "kaapana_dir": kaapana_dir,
            "build_dir": build_dir,
        }
    )

    config = merge_args_with_config(args, file_config)

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info("                       BUILD CONFIG                        ")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info(
        config.model_dump_json(
            indent=2, exclude={"registry_password", "registry_username"}
        )
    )
    Container.init_containers(
        container_engine=config.container_engine,
        enable_push=not config.build_only,
    )

    if not config.build_only and not config.no_login:
        container_registry_login(
            username=config.registry_username, password=config.registry_password
        )
        helm_registry_login(
            username=config.registry_username, password=config.registry_password
        )

    container_images_available = Container.collect_containers()
    BuildUtils.add_container_images_available(
        container_images_available=container_images_available
    )
    charts_available = HelmChart.collect_charts()

    init_helm_charts(
        save_tree=True,
        enable_push=not config.build_only,
        enable_lint=config.enable_linting,
        enable_kubeval=config.enable_linting,
    )

    progress = BuildProgress(started_at=time())
    startTime = time()
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD PLATFORM CHARTS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")

    HelmChart.generate_platform_build_tree()

    if BuildUtils.vulnerability_scan or BuildUtils.create_sboms:
        trivy_utils = BuildUtils.trivy_utils
        trivy_utils.tag = BuildUtils.platform_build_version

        def handler(signum, frame):
            BuildUtils.logger.info("Exiting...")

            trivy_utils.kill_flag = True

            with trivy_utils.semaphore_threadpool:
                if trivy_utils.threadpool is not None:
                    trivy_utils.threadpool.terminate()
                    trivy_utils.threadpool = None
            trivy_utils.error_clean_up()

            if BuildUtils.create_sboms:
                trivy_utils.safe_sboms()
            if BuildUtils.vulnerability_scan:
                trivy_utils.safe_vulnerability_reports()

            exit(1)

        signal.signal(signal.SIGTSTP, handler)

    # Create SBOMs if enabled
    if BuildUtils.create_sboms:
        trivy_utils.create_sboms(successful_built_containers)
    # Scan for vulnerabilities if enabled
    if BuildUtils.vulnerability_scan:
        trivy_utils.create_vulnerability_reports(successful_built_containers)

    # Check charts for configuation errors
    if BuildUtils.configuration_check:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ CHECK PLATFORM CHARTS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        for chart_object in BuildUtils.platform_filter:
            trivy_utils = BuildUtils.trivy_utils
            trivy_utils.tag = BuildUtils.platform_repo_version
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


if __name__ == "__main__":
    main()
