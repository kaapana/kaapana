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
        "--config", help="Path to build-config.yaml", default=argparse.SUPPRESS
    )
    parser.add_argument("--log-level", help="Log verbosity", default=argparse.SUPPRESS)
    parser.add_argument(
        "--default-registry", help="Docker registry", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--platform-filter",
        help="Comma-separated platform filter",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--external-source-dirs",
        help="Comma-separated external sources",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--build-ignore-patterns",
        help="Comma-separated ignore patterns",
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--username", default=argparse.SUPPRESS)
    parser.add_argument("--password", default=argparse.SUPPRESS)
    parser.add_argument("--build-only", action="store_true", default=argparse.SUPPRESS)
    parser.add_argument(
        "--enable-linting", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--exit-on-error", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument("--push-to-microk8s", default=argparse.SUPPRESS)
    parser.add_argument(
        "--create-offline-installation", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument("--parallel-processes", type=int, default=argparse.SUPPRESS)
    parser.add_argument(
        "--include-credentials", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--vulnerability-scan", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument("--vulnerability-severity-level", default=argparse.SUPPRESS)
    parser.add_argument(
        "--configuration-check", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--configuration-check-severity-level", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--create-sboms", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--enable-image-stats", action="store_true", default=argparse.SUPPRESS
    )
    parser.add_argument(
        "--latest",
        dest="version_latest",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--check-expired-vulnerabilities-database",
        action="store_true",
        default=argparse.SUPPRESS,
    )
    parser.add_argument("--kaapana-dir", default=argparse.SUPPRESS)
    parser.add_argument("--build-dir", default=argparse.SUPPRESS)
    parser.add_argument("--no-login", action="store_true", default=argparse.SUPPRESS)

    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Launch interactive selector to choose charts or containers to build",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--containers-to-build-by-charts",
        help="Comma-separated list of specific Helm charts to build their containers"
        "(default: ALL containers used by platform chart will be built)",
        default=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--containers-to-build",
        help="Comma-separated list of specific container images to build "
        "(default: ALL containers used by platform chart will be built)",
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
