#!/usr/bin/env python3
import sys
from pathlib import Path
from shutil import copyfile, rmtree
from time import time

from build_helper_v2.cli.config_loader import (
    load_yaml,
    merge_args_with_config,
    parse_args,
)
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.build_service import BuildService
from build_helper_v2.services.container_service import ContainerService
from build_helper_v2.services.helm_chart_service import HelmChartService
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.logger import get_logger, init_logger, set_console_level


def main():
    args = parse_args()

    script_dir = Path(__file__).resolve().parent.parent

    kaapana_dir = Path(getattr(args, "kaapana_dir", script_dir))
    build_dir = Path(getattr(args, "build_dir", kaapana_dir / "build"))
    config_path = Path(
        getattr(args, "config", kaapana_dir / "build-scripts" / "build-config.yaml")
    )

    if build_dir.exists():
        rmtree(build_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    init_logger(build_dir, log_level="DEBUG")
    logger = get_logger()
    logger.info("-----------------------------------------------------------")
    logger.info("--------------- loading build-configuration ---------------")
    logger.info("-----------------------------------------------------------")

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
    config_data = merge_args_with_config(args, file_config)
    config = BuildConfig(**config_data)
    set_console_level(config.log_level)

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info("                       BUILD CONFIG                        ")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    config.log_self(logger)

    build_state = BuildState(started_at=time())

    logger.info("-----------------------------------------------------------")

    ContainerService.init(config=config, build_state=build_state)
    ContainerService.verify_container_engine_installed()

    HelmChartService.init(config=config, build_state=build_state)
    HelmChartService.verify_helm_installed()

    if not config.build_only and not config.no_login:
        ContainerService.container_registry_login(
            username=config.registry_username, password=config.registry_password
        )
        HelmChartService.helm_registry_login(
            username=config.registry_username, password=config.registry_password
        )

    logger.info("-----------------------------------------------------------")
    ContainerService.collect_containers()
    ContainerService.resolve_base_images_into_container()
    HelmChartService.collect_charts()
    HelmChartService.resolve_chart_dependencies()
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD PLATFORM CHARTS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    
    selected_charts, selected_containers = BuildService.determine_build_targets(
        build_config=config, build_state=build_state
    )
    
    if not selected_charts:
        ContainerService.build_and_push_containers(selected_containers)
    else:
        # HelmChartService.generate_build_tree(selected_charts)
        # HelmChartService.build_and_push_charts(selected_charts)        
        ContainerService.build_and_push_containers(selected_containers)

    if config.vulnerability_scan:
        pass
        
    if config.create_sboms:
        pass
        # trivy_utils = BuildUtils.trivy_utils
        # trivy_utils.tag = BuildUtils.platform_build_version

        # def handler(signum, frame):
        #     logger.info("Exiting...")

        #     trivy_utils.kill_flag = True

        #     with trivy_utils.semaphore_threadpool:
        #         if trivy_utils.threadpool is not None:
        #             trivy_utils.threadpool.terminate()
        #             trivy_utils.threadpool = None
        #     trivy_utils.error_clean_up()

        #     if BuildUtils.create_sboms:
        #         trivy_utils.safe_sboms()
        #     if BuildUtils.vulnerability_scan:
        #         trivy_utils.safe_vulnerability_reports()

        #     exit(1)

        # signal.signal(signal.SIGTSTP, handler)

    # Create SBOMs if enabled
    # if BuildUtils.create_sboms:
    #     trivy_utils.create_sboms(successful_built_containers)
    # # Scan for vulnerabilities if enabled
    # if BuildUtils.vulnerability_scan:
    #     trivy_utils.create_vulnerability_reports(successful_built_containers)

    # # Check charts for configuation errors
    # if BuildUtils.configuration_check:
    #     logger.info("")
    #     logger.info("-----------------------------------------------------------")
    #     logger.info("------------------ CHECK PLATFORM CHARTS ------------------")
    #     logger.info("-----------------------------------------------------------")
    #     logger.info("")
    #     for chart_object in BuildUtils.platform_filter:
    #         trivy_utils = BuildUtils.trivy_utils
    #         trivy_utils.tag = BuildUtils.platform_repo_version
    #         trivy_utils.check_chart(
    #             path_to_chart=os.path.join(BuildUtils.build_dir, chart_object)
    #         )

    if len(IssueTracker.issues) > 0:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------------ ISSUES: --------------------------")
        logger.info("-----------------------------------------------------------")
        for issue in IssueTracker.issues:
            issue.log_self(logger)

    build_state.mark_finished()
    if build_state.duration:
        hours, rem = divmod(build_state.duration, 3600)
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
