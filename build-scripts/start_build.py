#!/usr/bin/env python3
import os
from dotenv import load_dotenv
from pathlib import Path
from shutil import rmtree
from time import time

from build_helper.build import (
    BuildConfig,
    BuildHelper,
    BuildState,
    IssueTracker,
    OfflineInstallerHelper,
    TrivyHelper,
)
from build_helper.cli.config_loader import parse_args
from build_helper.container import ContainerHelper
from build_helper.helm import HelmChartHelper
from build_helper.utils.logger import get_logger, init_logger, set_console_level


def main(build_config):
    if build_config.build_dir.exists():
        rmtree(build_config.build_dir)

    build_config.build_dir.mkdir(parents=True, exist_ok=True)
    init_logger(build_config.build_dir, log_level="DEBUG")
    logger = get_logger()
    logger.info("-----------------------------------------------------------")
    logger.info("--------------- loading build-configuration ---------------")
    logger.info("-----------------------------------------------------------")

    if not (build_config.kaapana_dir / "platforms").is_dir():
        logger.error(
            f"The directory `platforms` was not found in {build_config.kaapana_dir}."
        )
        exit(1)

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
    ContainerHelper.init(build_config=build_config, build_state=build_state)
    HelmChartHelper.init(build_config=build_config, build_state=build_state)
    BuildHelper.init(build_config=build_config, build_state=build_state)
    ContainerHelper.verify_container_engine_installed()
    HelmChartHelper.verify_helm_installed()

    if not build_config.build_only and not build_config.no_login:
        ContainerHelper.container_registry_login(
            username=build_config.registry_username,
            password=build_config.registry_password,
        )
        HelmChartHelper.helm_registry_login(
            username=build_config.registry_username,
            password=build_config.registry_password,
        )

    logger.info("-----------------------------------------------------------")
    ContainerHelper.collect_containers()
    ContainerHelper.resolve_base_images_into_container()
    HelmChartHelper.collect_charts()
    HelmChartHelper.resolve_chart_dependencies()
    HelmChartHelper.resolve_kaapana_collections()
    HelmChartHelper.resolve_preinstall_extensions()

    platform_chart = BuildHelper.get_platform_chart()
    BuildHelper.generate_build_graph(platform_chart)
    BuildHelper.generate_build_tree(platform_chart)
    BuildHelper.generate_deployment_script(platform_chart)

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD CHARTS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    HelmChartHelper.build_and_push_charts(platform_chart=platform_chart)

    if not build_config.only_charts:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ BUILD CONTAINERS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        BuildHelper.select_containers_to_build()
        ContainerHelper.build_and_push_containers()

        if build_config.create_offline_installation:
            OfflineInstallerHelper.init(
                build_config=build_config, build_state=build_state
            )
            OfflineInstallerHelper.generate_microk8s_offline_version(
                platform_chart.build_chart_dir
            )

            images_tarball_path = (
                platform_chart.build_chart_dir.parent
                / f"{platform_chart.name}-{platform_chart.version}-images.tar"
            )
            OfflineInstallerHelper.export_image_list_into_tarball(
                image_list=[c.tag for c in build_state.selected_containers],
                images_tarball_path=images_tarball_path,
                container_engine=build_config.container_engine,
            )
            logger.info("Finished: Generating platform images tarball.")

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

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("--------------------GENERATE REPORT -----------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")

    BuildHelper.generate_report()

    if build_config.configuration_check:
        TrivyHelper.init(build_config=build_config, build_state=build_state)
        TrivyHelper.misconfiguration_check()

    if build_config.create_sboms:
        TrivyHelper.init(build_config=build_config, build_state=build_state)
        TrivyHelper.create_sboms()

    if build_config.vulnerability_scan:
        TrivyHelper.init(build_config=build_config, build_state=build_state)
        TrivyHelper.vulnerability_scan()

    logger.info("-----------------------------------------------------------")
    logger.info("-------------------------- DONE ---------------------------")
    logger.info("-----------------------------------------------------------")


if __name__ == "__main__":
    load_dotenv(Path(os.getcwd(), ".env"))
    args = parse_args()
    build_config = BuildConfig(**vars(args))

    main(build_config)
