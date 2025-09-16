import argparse
import os
from pathlib import Path

import yaml


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments for Kaapana Platform Builder.

    Uses `argparse.SUPPRESS` so that arguments not set in the CLI
    are not included in the returned Namespace.

    Returns:
        argparse.Namespace: Parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Kaapana Platform Builder")

    parser.add_argument(
        "-c",
        "--config",
        help="Path to build-config.yaml",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ll",
        "--log-level",
        help="Set logging verbosity (e.g. DEBUG, INFO, WARNING, ERROR).",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-dr",
        "--default-registry",
        help="Name of the Docker registry to build and push images to.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-pf",
        "--platform-filter",
        help="Comma-separated list of platform chart names to build.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-es",
        "--external-source-dirs",
        help="Comma-separated external directories to search for containers and charts.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-bip",
        "--build-ignore-patterns",
        help="Comma-separated list of directories or files to exclude from build.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-u",
        "--username",
        help="Username for registry authentication.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-p",
        "--password",
        help="Password for registry authentication.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-bo",
        "--build-only",
        help="Only build containers and charts (do not push).",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-el",
        "--enable-linting",
        help="Enable Helm chart linting and kubeval validation.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ee",
        "--exit-on-error",
        help="Stop the build process immediately if an error occurs.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-pm",
        "--push-to-microk8s",
        help="Push built images into MicroK8s registry.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-oi",
        "--create-offline-installation",
        help="Create a docker image dump for offline platform installation.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-pp",
        "--parallel-processes",
        help="Number of parallel processes for container build + push.",
        type=int,
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ic",
        "--include-credentials",
        help="Include registry credentials in deploy-platform script.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-vs",
        "--vulnerability-scan",
        help="Scan built containers with Trivy for vulnerabilities.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-vsl",
        "--vulnerability-severity-level",
        help="Filter vulnerabilities by severity (CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN).",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-cc",
        "--configuration-check",
        help="Check charts, deployments, Dockerfiles, etc. for configuration errors.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-ccl",
        "--configuration-check-severity-level",
        help="Filter configuration check findings by severity "
        "(CRITICAL, HIGH, MEDIUM, LOW, UNKNOWN).",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-sbom",
        "--create-sboms",
        help="Generate SBOMs (Software Bill of Materials) for built containers.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-is",
        "--enable-image-stats",
        help="Enable container image size statistics (writes image_stats.json).",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--latest",
        dest="version_latest",
        help="Force version tag to 'latest'.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-cevd",
        "--check-expired-vulnerabilities-database",
        help="Check if vulnerability database is expired and rescan if necessary.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-kd",
        "--kaapana-dir",
        help="Path to the Kaapana repository directory.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-bd",
        "--build-dir",
        help="Path to the main Kaapana repo-dir to build from.",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-nl",
        "--no-login",
        help="Skip login to registry (expects to already be logged in).",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-i",
        "--interactive",
        help="Launch interactive selector to choose charts or containers to build.",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-cbc",
        "--containers-to-build-by-charts",
        help="Comma-separated list of Helm charts whose containers should be built "
        "(default: all containers used by platform charts).",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "-cb",
        "--containers-to-build",
        help="Comma-separated list of specific container images to build "
        "(default: all containers used by platform charts).",
        default=argparse.SUPPRESS,
    )

    parser.add_argument(
        "-oc",
        "--only-charts",
        help="Skip docker build and docker push completely and only package and push charts",
        action="store_true",
        default=argparse.SUPPRESS,
    )

    return parser.parse_args()


def apply_env_fallbacks(config: dict) -> dict:
    """
    Apply environment variable fallbacks to a configuration dictionary.

    Only sets values if they are not already present in `config`.

    Args:
        config (dict): Configuration dictionary.

    Returns:
        dict: Configuration dictionary with environment fallbacks applied.
    """
    if not config.get("http_proxy"):
        config["http_proxy"] = os.getenv("http_proxy")

    if not config.get("registry_username"):
        config["registry_username"] = os.getenv("REGISTRY_USER")

    if not config.get("registry_password"):
        config["registry_password"] = os.getenv("REGISTRY_PW")

    return config


def load_yaml(path: Path) -> dict:
    """
    Load a YAML file safely.

    Args:
        path (Path): Path to the YAML file.

    Returns:
        dict: Loaded YAML content as a dictionary, or empty dict if file does not exist.
    """
    if not path.exists():
        return {}
    with path.open("r") as stream:
        return yaml.safe_load(stream) or {}


def merge_args_with_config(args: argparse.Namespace, config_data: dict):
    """
    Merge command-line arguments with a configuration dictionary.

    Command-line arguments take priority over the configuration dictionary.
    Applies environment variable fallbacks afterwards.

    Args:
        args (argparse.Namespace): Parsed CLI arguments.
        config_data (dict): Configuration data loaded from YAML.

    Returns:
        dict: Merged configuration dictionary.
    """
    cli_dict = {k: v for k, v in vars(args).items() if v is not None}
    config_data.update(cli_dict)
    config_data = apply_env_fallbacks(config_data)
    return config_data
