#!/usr/bin/env python3
import sys
from pathlib import Path
from shutil import rmtree
from time import time
from typing import List, Optional

import typer
from dotenv import load_dotenv

from build_cli.build import (
    BuildConfig,
    BuildHelper,
    BuildState,
    IssueTracker,
    OfflineInstallerHelper,
    TrivyHelper,
)
from build_cli.container import ContainerHelper
from build_cli.container.coordinator import BuildCoordinator
from build_cli.helm import HelmChartHelper
from build_cli.utils.logger import get_logger, init_logger, set_console_level


def _find_kaapana_root(start: Optional[Path] = None) -> Optional[Path]:
    """Walk up from ``start`` (default: cwd) to the nearest Kaapana repo root.

    A Kaapana checkout is identified by a top-level ``platforms/`` directory — the
    same marker ``run_build`` and ``BuildConfig.validate_all`` already validate.
    Resolving from the cwd (not ``__file__``) means an editable-installed CLI builds
    whichever worktree it is invoked from. Returns None when no ancestor qualifies
    (i.e. invoked outside a Kaapana worktree). ``KAAPANA_DIR`` / ``--kaapana-dir``
    still override this.
    """
    start = (start or Path.cwd()).resolve()
    for parent in (start, *start.parents):
        if (parent / "platforms").is_dir():
            return parent
    return None


app = typer.Typer(
    help="Kaapana Platform Builder",
    pretty_exceptions_show_locals=False,
    pretty_exceptions_short=True,
)


@app.command()
def build(
    log_level: str = typer.Option(
        "INFO",
        "-ll",
        "--log-level",
        envvar="LOG_LEVEL",
        help="Set logging verbosity (DEBUG, INFO, WARNING, ERROR).",
    ),
    default_registry: str = typer.Option(
        "",
        "-dr",
        "--default-registry",
        envvar="DEFAULT_REGISTRY",
        help="Name of the Docker registry to build and push images to.",
    ),
    platform_filter: str = typer.Option(
        "kaapana-admin-chart",
        "-pf",
        "--platform-filter",
        envvar="PLATFORM_FILTER",
        help="Platform chart names to build.",
    ),
    external_source_dirs: List[str] = typer.Option(
        [],
        "-es",
        "--external-source-dirs",
        envvar="EXTERNAL_SOURCE_DIRS",
        help="External directories to search for containers and charts.",
    ),
    build_ignore_patterns: str = typer.Option(
        "*templates_and_examples/*,*ci/*,*lib/task_api/*",
        "-bip",
        "--build-ignore-patterns",
        envvar="BUILD_IGNORE_PATTERNS",
        help="Directories or files to exclude from build.",
    ),
    username: str = typer.Option(
        "",
        "-u",
        "--username",
        "--registry-username",
        envvar="REGISTRY_USER",
        help="Username for registry authentication.",
    ),
    password: str = typer.Option(
        "",
        "-p",
        "--registry-password",
        "--registry-pw",
        envvar="REGISTRY_PW",
        help="Password for registry authentication.",
    ),
    build_only: bool = typer.Option(
        False,
        "-bo",
        "--build-only",
        envvar="BUILD_ONLY",
        help="Only build containers and charts (do not push).",
    ),
    scan_only: bool = typer.Option(
        False,
        "-so",
        "--scan-only",
        envvar="SCAN_ONLY",
        help="Skip building/pushing; run the selected Trivy scans against the registry images of this version.",
    ),
    enable_linting: bool = typer.Option(
        True,
        "-el/--no-linting",
        "--enable-linting/--no-linting",
        envvar="ENABLE_LINTING",
        help="Enable Helm chart linting and kubeval validation.",
    ),
    exit_on_error: bool = typer.Option(
        True,
        "-ee/--no-exit-on-error",
        "--exit-on-error/--no-exit-on-error",
        envvar="EXIT_ON_ERROR",
        help="Stop immediately if an error occurs.",
    ),
    push_to_microk8s: bool = typer.Option(
        False,
        "-pm",
        "--push-to-microk8s",
        envvar="PUSH_TO_MICROK8S",
        help="Push built images into MicroK8s registry.",
    ),
    create_offline_installation: bool = typer.Option(
        False,
        "-oi",
        "--create-offline-installation",
        envvar="CREATE_OFFLINE_INSTALLATION",
        help="Create an offline installation image dump.",
    ),
    publish_offline_installer: bool = typer.Option(
        False,
        "--publish-offline-installer",
        envvar="PUBLISH_OFFLINE_INSTALLER",
        help="Also publish the offline installer as 'offline-installer:<version>'. Requires --create-offline-installation and registry login.",
    ),
    skip_platform_images_tarball: bool = typer.Option(
        False,
        "--skip-platform-images-tarball",
        envvar="SKIP_PLATFORM_IMAGES_TARBALL",
        help="Skip the (large) platform images tarball. Use when targets pull these images from the registry instead of a true air-gap import.",
    ),
    offline_image_platform: Optional[str] = typer.Option(
        None,
        "--offline-image-platform",
        envvar="OFFLINE_IMAGE_PLATFORM",
        help="Container image platform for offline installer tarballs, e.g. linux/amd64 or linux/arm64. Defaults to the build host platform.",
    ),
    offline_extra_files: List[str] = typer.Option(
        [],
        "--offline-extra-file",
        envvar="OFFLINE_EXTRA_FILES",
        help="Extra file/dir to include in the offline installer tar as SRC[:DST] (repeatable; DST is relative to the installer root, default = basename).",
    ),
    parallel_processes: int = typer.Option(
        2,
        "-pp",
        "--parallel-processes",
        envvar="PARALLEL_PROCESSES",
        help="Number of parallel build processes.",
    ),
    vulnerability_scan: bool = typer.Option(
        False,
        "-vs",
        "--vulnerability-scan",
        envvar="VULNERABILITY_SCAN",
        help="Scan containers for vulnerabilities.",
    ),
    vulnerability_severity_level: str = typer.Option(
        "CRITICAL,HIGH",
        "-vsl",
        "--vulnerability-severity-level",
        envvar="VULNERABILITY_SEVERITY_LEVEL",
        help="Filter vulnerabilities by severity.",
    ),
    configuration_check: bool = typer.Option(
        False,
        "-cc",
        "--configuration-check",
        envvar="CONFIGURATION_CHECK",
        help="Run configuration checks.",
    ),
    configuration_check_severity_level: str = typer.Option(
        "CRITICAL,HIGH",
        "-ccl",
        "--configuration-check-severity-level",
        envvar="CONFIGURATION_CHECK_SEVERITY_LEVEL",
        help="Filter configuration findings by severity.",
    ),
    create_sboms: bool = typer.Option(
        False,
        "-sbom",
        "--create-sboms",
        envvar="CREATE_SBOMS",
        help="Generate SBOMs for built containers.",
    ),
    enable_image_stats: bool = typer.Option(
        False,
        "-is",
        "--enable-image-stats",
        envvar="ENABLE_IMAGE_STATS",
        help="Write image size statistics.",
    ),
    version_latest: bool = typer.Option(
        False,
        "--latest",
        envvar="USE_LATEST_TAG",
        help="Force version tag to 'latest'.",
    ),
    check_expired_vulnerability_db: bool = typer.Option(
        False,
        "-cevd",
        "--check-expired-vulnerabilities-database",
        envvar="CHECK_EXPIRED_VULNERABILITY_DB",
        help="Check and refresh vulnerability database.",
    ),
    kaapana_dir: Optional[Path] = typer.Option(
        None,
        "-kd",
        "--kaapana-dir",
        envvar="KAAPANA_DIR",
        help="Path to Kaapana repository. Defaults to the worktree containing the current directory.",
    ),
    build_dir: Optional[Path] = typer.Option(
        None,
        "-bd",
        "--build-dir",
        envvar="BUILD_DIR",
        help="Directory for build artifacts. Defaults to <kaapana-dir>/build.",
    ),
    no_login: bool = typer.Option(
        False,
        "-nl",
        "--no-login",
        envvar="NO_LOGIN",
        help="Skip registry login.",
    ),
    interactive: bool = typer.Option(
        False,
        "-i",
        "--interactive",
        envvar="INTERACTIVE",
        help="Launch interactive selector.",
    ),
    containers_to_build_by_charts: List[str] = typer.Option(
        [],
        "-cbc",
        "--containers-to-build-by-charts",
        envvar="CONTAINERS_TO_BUILD_BY_CHARTS",
        help="Charts whose containers should be built.",
    ),
    containers_to_build: List[str] = typer.Option(
        [],
        "-cb",
        "--containers-to-build",
        envvar="CONTAINERS_TO_BUILD",
        help="Specific container images to build.",
    ),
    only_charts: bool = typer.Option(
        False,
        "-oc",
        "--only-charts",
        envvar="ONLY_CHARTS",
        help="Only package and push charts.",
    ),
    include_model_weights: bool = typer.Option(
        False,
        "--include-model-weights",
        envvar="INCLUDE_MODEL_WEIGHTS",
        help="Download pretrained model weights during build.",
    ),
    http_proxy: Optional[str] = typer.Option(
        "",
        "--http-proxy",
        envvar="http_proxy",
        help="HTTP proxy for outbound connections.",
    ),
    plain_http: bool = typer.Option(
        False,
        "--plain-http",
        envvar="PLAIN_HTTP",
        help="Use plain HTTP for communication.",
    ),
    helm_executable: str = typer.Option(
        "helm",
        "--helm-executable",
        envvar="HELM_EXECUTABLE",
        help="Helm executable to use.",
    ),
    container_engine: str = typer.Option(
        "docker",
        "--container-engine",
        envvar="CONTAINER_ENGINE",
        help="Container engine to use (docker or podman). Registry build cache "
        "(--cache-from/--cache-to) requires docker.",
    ),
    cache_from: bool = typer.Option(
        False,
        "--cache-from/--no-cache-from",
        "-cf",
        envvar="CACHE_FROM",
        help="Use build cache from registry.",
    ),
    cache_to: bool = typer.Option(
        False,
        "--cache-to/--no-cache-to",
        "-ct",
        envvar="CACHE_TO",
        help="Push build cache to registry.",
    ),
    cache_to_registry: Optional[str] = typer.Option(
        None,
        "-ctreg",
        "--cache-to-registry",
        envvar="CACHE_TO_REGISTRY",
        help="Registry and namespace to push the build cache to. Defaults to --default-registry.",
    ),
    cache_to_username: Optional[str] = typer.Option(
        None,
        "--cache-to-username",
        envvar="CACHE_TO_USER",
        help="Username for the cache-to registry. Defaults to --username.",
    ),
    cache_to_password: Optional[str] = typer.Option(
        None,
        "--cache-to-password",
        envvar="CACHE_TO_PW",
        help="Password for the cache-to registry. Defaults to --registry-password.",
    ),
    cache_from_registry: Optional[str] = typer.Option(
        None,
        "-cfreg",
        "--cache-from-registry",
        envvar="CACHE_FROM_REGISTRY",
        help="Registry and namespace to pull the build cache from. Defaults to --default-registry.",
    ),
    cache_from_username: Optional[str] = typer.Option(
        None,
        "--cache-from-username",
        envvar="CACHE_FROM_USER",
        help="Username for the cache-from registry. Defaults to --username.",
    ),
    cache_from_password: Optional[str] = typer.Option(
        None,
        "--cache-from-password",
        envvar="CACHE_FROM_PW",
        help="Password for the cache-from registry. Defaults to --registry-password.",
    ),
    cache_tag: Optional[str] = typer.Option(
        "cache",
        "-ctag",
        "--cache-tag",
        envvar="CACHE_TAG",
        help="Image version/tag for the build cache in the registry.",
    ),
    keep_buildx_builder: bool = typer.Option(
        False,
        "--keep-buildx-builder",
        envvar="KEEP_BUILDX_BUILDER",
        help="Keep the dedicated kaapana-buildx builder after the build completes "
        "instead of removing it. Only relevant with --cache-from/--cache-to.",
    ),
):
    """
    Kaapana Platform Builder entry point.
    """
    if kaapana_dir is None:
        kaapana_dir = _find_kaapana_root()
        if kaapana_dir is None:
            typer.secho(
                "kaapana-build must be run from inside a Kaapana worktree "
                "(no 'platforms/' directory found in the current directory or any parent).\n"
                "cd into a Kaapana worktree, or pass --kaapana-dir / set KAAPANA_DIR.",
                err=True,
                fg=typer.colors.RED,
            )
            raise typer.Exit(1)
    if build_dir is None:
        build_dir = kaapana_dir / "build"

    config = BuildConfig(
        default_registry=default_registry,
        registry_username=username,
        registry_password=password,
        platform_filter=platform_filter,
        external_source_dirs=[Path(d) for d in external_source_dirs],
        build_ignore_patterns=build_ignore_patterns,
        build_only=build_only,
        scan_only=scan_only,
        enable_linting=enable_linting,
        exit_on_error=exit_on_error,
        log_level=log_level,
        push_to_microk8s=push_to_microk8s,
        create_offline_installation=create_offline_installation,
        publish_offline_installer=publish_offline_installer,
        skip_platform_images_tarball=skip_platform_images_tarball,
        offline_image_platform=offline_image_platform,
        offline_extra_files=offline_extra_files,
        parallel_processes=parallel_processes,
        vulnerability_scan=vulnerability_scan,
        vulnerability_severity_level=vulnerability_severity_level,
        configuration_check=configuration_check,
        configuration_check_severity_level=configuration_check_severity_level,
        create_sboms=create_sboms,
        enable_image_stats=enable_image_stats,
        version_latest=version_latest,
        check_expired_vulnerability_db=check_expired_vulnerability_db,
        kaapana_dir=kaapana_dir,
        build_dir=build_dir,
        no_login=no_login,
        interactive=interactive,
        containers_to_build_by_charts=containers_to_build_by_charts,
        containers_to_build=containers_to_build,
        only_charts=only_charts,
        include_model_weights=include_model_weights,
        http_proxy=http_proxy,
        plain_http=plain_http,
        helm_executable=helm_executable,
        container_engine=container_engine,
        cache_from=cache_from,
        cache_to=cache_to,
        cache_to_registry=cache_to_registry,
        cache_to_username=cache_to_username,
        cache_to_password=cache_to_password,
        cache_from_registry=cache_from_registry,
        cache_from_username=cache_from_username,
        cache_from_password=cache_from_password,
        cache_tag=cache_tag,
        keep_buildx_builder=keep_buildx_builder,
    )
    run_build(build_config=config)


def validate_registry_login_config(build_config: BuildConfig, logger) -> None:
    if build_config.build_only or build_config.no_login:
        return

    missing = []
    if not build_config.default_registry:
        missing.append("--default-registry")
    if not build_config.registry_username:
        missing.append("--username/--registry-username")
    if not build_config.registry_password:
        missing.append("--registry-password")

    if not missing:
        return

    logger.error(
        "Registry login is enabled, but required registry settings are missing."
    )
    logger.error(f"Missing: {', '.join(missing)}")
    logger.error("How to use this command:")
    logger.error("  - Local build only: kaapana-build --latest --build-only --no-login")
    logger.error(
        "  - Build and push: kaapana-build --latest --default-registry <registry> --username <user> --registry-password <password>"
    )
    sys.exit(2)


def run_build(build_config: BuildConfig):
    EXIT_CODE = 0
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
    validate_registry_login_config(build_config, logger)

    build_state = BuildState(started_at=time())

    logger.info("-----------------------------------------------------------")
    ContainerHelper.init(build_config=build_config, build_state=build_state)
    HelmChartHelper.init(build_config=build_config, build_state=build_state)
    BuildHelper.init(build_config=build_config, build_state=build_state)
    ContainerHelper.verify_container_engine_installed()
    ContainerHelper.ensure_buildx_builder()
    HelmChartHelper.verify_helm_installed()

    if not build_config.build_only and not build_config.no_login:
        ContainerHelper.container_registry_login(
            registry=build_config.default_registry,
            username=build_config.registry_username,
            password=build_config.registry_password,
        )
        HelmChartHelper.helm_registry_login(
            username=build_config.registry_username,
            password=build_config.registry_password,
        )
        if build_config.cache_enabled:
            ContainerHelper.login_cache_registries()

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

    if not build_config.scan_only:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------ BUILD CHARTS ------------------")
        logger.info("-----------------------------------------------------------")
        logger.info("")
        HelmChartHelper.build_and_push_charts(platform_chart=platform_chart)

    if not build_config.only_charts:
        BuildHelper.select_containers_to_build()
        if build_config.scan_only:
            logger.info("Scan-only: skipping chart and container builds")
        else:
            logger.info("")
            logger.info("-----------------------------------------------------------")
            logger.info("------------------ BUILD CONTAINERS ------------------")
            logger.info("-----------------------------------------------------------")
            logger.info("")
            containers = ContainerHelper._build_state.selected_containers
            coordinator = BuildCoordinator(containers)
            coordinator.start()

            if (
                build_config.create_offline_installation
                or build_config.publish_offline_installer
            ):
                OfflineInstallerHelper.init(
                    build_config=build_config, build_state=build_state
                )
                OfflineInstallerHelper.handle_offline_installation(platform_chart)

    if len(IssueTracker.issues) > 0:
        logger.info("")
        logger.info("-----------------------------------------------------------")
        logger.info("------------------------ ISSUES: --------------------------")
        logger.info("-----------------------------------------------------------")
        for issue in IssueTracker.issues:
            issue.log_self(logger)

        if build_config.exit_on_error:
            EXIT_CODE = 1

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

    if not build_config.scan_only:
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

    ContainerHelper.remove_buildx_builder()

    logger.info("-----------------------------------------------------------")
    logger.info("-------------------------- DONE ---------------------------")
    logger.info("-----------------------------------------------------------")
    sys.exit(EXIT_CODE)


def main() -> None:
    """Console-script entrypoint (``kaapana-build``).

    Loads ``.env`` from the current working directory before dispatching to the
    Typer app. This must live in a function the ``[project.scripts]`` entrypoint
    calls directly — code under ``if __name__ == "__main__"`` does NOT run when
    the module is imported by the installed console script.
    """
    root = _find_kaapana_root() or Path.cwd()
    load_dotenv(root / ".env")
    app()


if __name__ == "__main__":
    main()
