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
from build_helper_v2.helper.build_helper import BuildHelper
from build_helper_v2.helper.container_helper import ContainerHelper
from build_helper_v2.helper.helm_chart_helper import HelmChartHelper
from build_helper_v2.helper.issue_tracker import IssueTracker
from build_helper_v2.helper.offline_installer_helper import OfflineInstallerHelper
from build_helper_v2.helper.trivy_helper import TrivyHelper
from build_helper_v2.models.build_config import BuildConfig
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

    logger.info("")
    logger.info("-----------------------------------------------------------")
    logger.info("------------------ BUILD CONTAINERS ------------------")
    logger.info("-----------------------------------------------------------")
    logger.info("")
    BuildHelper.select_containers_to_build()
    ContainerHelper.build_and_push_containers()

    if build_config.create_offline_installation:
        OfflineInstallerHelper.init(build_config=build_config, build_state=build_state)
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
        TrivyHelper.configuration_check()

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
    main()
