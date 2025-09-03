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
from build_helper_v2.services.trivy_service import TrivyService
from build_helper_v2.utils.logger import get_logger, init_logger, set_console_level


def main():
    args = parse_args()

    script_dir = Path(__file__).resolve().parent.parent

    kaapana_dir = Path(getattr(args, "kaapana_dir", script_dir))
    build_dir = Path(getattr(args, "build_dir", kaapana_dir / "build"))
    config_path = Path(
        getattr(args, "config", kaapana_dir / "build-scripts" / "build-config.yaml")
    )

    # if build_dir.exists():
    #     rmtree(build_dir)

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
    build_config = BuildConfig(**config_data)
    set_console_level(build_config.log_level)

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    logger.info("                       BUILD CONFIG                        ")
    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    build_config.log_self(logger)

    build_state = BuildState(started_at=time())

    logger.info("-----------------------------------------------------------")
    ContainerService.init(build_config=build_config, build_state=build_state)
    HelmChartService.init(build_config=build_config, build_state=build_state)
    BuildService.init(build_config=build_config, build_state=build_state)
    ContainerService.verify_container_engine_installed()
    HelmChartService.verify_helm_installed()

    if not build_config.build_only and not build_config.no_login:
        ContainerService.container_registry_login(
            username=build_config.registry_username,
            password=build_config.registry_password,
        )
        HelmChartService.helm_registry_login(
            username=build_config.registry_username,
            password=build_config.registry_password,
        )

    logger.info("-----------------------------------------------------------")
    ContainerService.collect_containers()
    ContainerService.resolve_base_images_into_container()
    HelmChartService.collect_charts()
    HelmChartService.resolve_chart_dependencies()

    BuildService.determine_build_targets()  # Updates build_state

    if not build_state.selected_charts:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ BUILD CONTAINERS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        ContainerService.build_and_push_containers()
    else:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ BUILD CHARTS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        HelmChartService.build_and_push_charts()
        ContainerService.build_and_push_containers()

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
    logger.info("--------------------GENERATE REPORT -----------------------")
    logger.info("-----------------------------------------------------------")
    BuildService.generate_report()

    if build_config.configuration_check:
        TrivyService.init(build_config=build_config, build_state=build_state)
        TrivyService.configuration_check()

    if build_config.create_sboms:
        TrivyService.init(build_config=build_config, build_state=build_state)
        TrivyService.create_sboms()

    if build_config.vulnerability_scan:
        TrivyService.init(build_config=build_config, build_state=build_state)
        TrivyService.vulnerability_scan()

    logger.info("-----------------------------------------------------------")
    logger.info("-------------------------- DONE ---------------------------")
    logger.info("-----------------------------------------------------------")


if __name__ == "__main__":
    main()
