#!/usr/bin/env python3
import os
from pathlib import Path
from typing import List, Optional

import start_build
import typer
from build_helper.build import build_config
from dotenv import load_dotenv

app = typer.Typer(help="Kaapana Platform Builder")


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
        "templates_and_examples,ci,lib/task_api",
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
    parallel_processes: int = typer.Option(
        2,
        "-pp",
        "--parallel-processes",
        envvar="PARALLEL_PROCESSES",
        help="Number of parallel build processes.",
    ),
    include_credentials: bool = typer.Option(
        False,
        "-ic",
        "--include-credentials",
        envvar="INCLUDE_CREDENTIALS",
        help="Include registry credentials in deploy script.",
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
    kaapana_dir: Path = typer.Option(
        Path(__file__).resolve().parent.parent,
        "-kd",
        "--kaapana-dir",
        envvar="KAAPANA_DIR",
        help="Path to Kaapana repository.",
    ),
    build_dir: Path = typer.Option(
        Path(__file__).resolve().parent.parent / "build",
        "-bd",
        "--build-dir",
        envvar="BUILD_DIR",
        help="Directory for build artifacts.",
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
        help="Container engine to use (docker or podman).",
    ),
):
    """
    Kaapana Platform Builder entry point.
    """
    # Business logic goes here

    config = build_config.BuildConfig(
        default_registry=default_registry,
        registry_username=username,
        registry_password=password,
        platform_filter=platform_filter,
        external_source_dirs=[Path(d) for d in external_source_dirs],
        build_ignore_patterns=build_ignore_patterns,
        build_only=build_only,
        enable_linting=enable_linting,
        exit_on_error=exit_on_error,
        log_level=log_level,
        push_to_microk8s=push_to_microk8s,
        create_offline_installation=create_offline_installation,
        parallel_processes=parallel_processes,
        include_credentials=include_credentials,
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
    )
    start_build.main(build_config=config)


if __name__ == "__main__":
    load_dotenv(Path(os.getcwd(), ".env"))
    app()
