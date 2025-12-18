import os
import re
import shutil
import warnings
from pathlib import Path
from typing import Any, Dict, Generator, Optional

import requests
from kaapanapy.logger import get_logger
from pydantic import Field, ValidationError, model_validator
from pydantic_settings import BaseSettings

logger = get_logger(__name__, level="DEBUG")

REGEX = r"image=(\"|\'|f\"|f\')([\w\-\\{\}.]+)(\/[\w\-\.]+|)\/([\w\-\.]+):([\w\-\\{\}\.]+)(\"|\'|f\"|f\')"


class Settings(BaseSettings):
    """
    Configuration settings loaded from environment variables or defaults.

    Attributes:
        tmp_prefix (str): Temporary directory path containing files to process.
        target_prefix (str): Target directory where files will be copied or removed.
        action (str): Action to perform: "copy", "remove", or "prefetch".
        admin_namespace (Optional[str]): Kubernetes namespace for Helm-related services.
        services_namespace (Optional[str]): Kubernetes namespace for Airflow services.
        kaapana_build_version (Optional[str]): Build version tag for Kaapana images.
        kaapana_default_registry (Optional[str]): Default Docker registry URL for images.
        docker_version (Optional[str]): Optional Docker version tag; defaults to kaapana_build_version if unset.

    Properties:
        helm_api (Optional[str]): Constructs Helm API base URL from admin_namespace.
        airflow_api (Optional[str]): Constructs Airflow API trigger URL from services_namespace.
        docker_version_effective (Optional[str]): Effective Docker version to use, preferring docker_version over kaapana_build_version.

    Validators:
        validate_conditionally_required: Ensures certain environment variables are set
            when working with workflows under the mounted workflows directory.
    """

    tmp_prefix: str = "/kaapana/tmp/"
    target_prefix: str = Field(
        default_factory=lambda: os.getenv("TARGET_PREFIX", "/kaapana/mounted/workflows")
    )
    action: str = Field(default_factory=lambda: os.getenv("ACTION", "copy"))

    admin_namespace: Optional[str] = Field(default=None, alias="ADMIN_NAMESPACE")
    services_namespace: Optional[str] = Field(default=None, alias="SERVICES_NAMESPACE")
    kaapana_build_version: Optional[str] = Field(
        default=None, alias="KAAPANA_BUILD_VERSION"
    )
    kaapana_default_registry: Optional[str] = Field(
        default=None, alias="KAAPANA_DEFAULT_REGISTRY"
    )
    docker_version: Optional[str] = Field(default=None, alias="DOCKER_VERSION")

    @property
    def helm_api(self) -> Optional[str]:
        if self.admin_namespace:
            return f"http://kube-helm-service.{self.admin_namespace}.svc:5000"
        return None

    @property
    def airflow_api(self) -> Optional[str]:
        if self.services_namespace:
            return (
                f"http://airflow-webserver-service.{self.services_namespace}.svc:8080/"
                f"flow/kaapana/api/trigger/service-daily-cleanup-jobs"
            )
        return None

    @property
    def docker_version_effective(self) -> Optional[str]:
        """
        Returns the effective Docker version to use.

        Returns:
            str | None: The docker_version if set; otherwise the kaapana_build_version.
        """
        return self.docker_version or self.kaapana_build_version

    @model_validator(mode="after")
    def validate_conditionally_required(self) -> "Settings":
        # Only validate if workflows are involved
        if self.target_prefix.startswith("/kaapana/mounted/workflows"):
            missing = []
            if not self.kaapana_build_version:
                missing.append("KAAPANA_BUILD_VERSION")
            if not self.kaapana_default_registry:
                missing.append("KAAPANA_DEFAULT_REGISTRY")
            if not self.admin_namespace:
                missing.append("ADMIN_NAMESPACE")
            if not self.services_namespace:
                missing.append("SERVICES_NAMESPACE")

            if missing:
                raise ValueError(
                    f"The following environment variables must be set when "
                    f"target_prefix starts with '/kaapana/mounted/workflows': {', '.join(missing)}"
                )
        return self


def listdir_nohidden(path: Path, target_prefix: str) -> Generator[Path, None, None]:
    """
    Generator yielding non-hidden, relevant files or directories from a path.

    - Skips hidden files and directories.
    - Returns an empty generator if the directory does not exist.
    - Returns Path objects (not strings) for consistency.

    Args:
        path (Path): Directory to scan.
        target_prefix (str): Used to determine filtering rules for workflows.

    Yields:
        Path: File or directory paths matching the visibility criteria.
    """
    if not path.exists():
        logger.debug("Skipping non-existent path: %s", path)
        return
    if not path.is_dir():
        logger.debug("Skipping non-directory path: %s", path)
        return

    try:
        for f in path.iterdir():
            if target_prefix.startswith("/kaapana/mounted/workflows"):
                if (
                    not f.name.endswith(".pyc")
                    and not f.name.startswith(".")
                    and not (f.name.startswith("__") and f.name.endswith("__"))
                ):
                    yield f
            elif f.name.endswith(".tgz"):
                yield f
    except Exception as e:
        logger.warning("Warning for listing directory %s: %s", path, e)


def get_images(target_dir: str, settings: Settings) -> Dict[str, Any]:
    """
    Scans Python files under a given directory for Docker image references.

    Matches custom image tags using a regex and replaces placeholders with
    actual values from the environment. Returns a dictionary of image metadata
    for triggering remote pull operations.

    Args:
        target_dir (str): The directory containing files to scan.
        settings (Settings): The configuration settings with env context.

    Returns:
        Dict[str, Any]: A dictionary mapping image strings to metadata.
    """
    logger.info("Searching for images...")
    image_dict = {}

    for file_path in Path(target_dir).rglob("*.py"):
        if not file_path.is_file():
            logger.debug("Skipping directory: %s", file_path)
            continue

        logger.debug("Checking file: %s", file_path)
        content = file_path.read_text()

        for match in re.findall(REGEX, content):
            match = list(match)
            registry = match[1].replace("{default_registry}", "{DEFAULT_REGISTRY}")
            registry_url = registry.replace(
                "{DEFAULT_REGISTRY}", settings.kaapana_default_registry or ""
            )

            image = match[3]
            version = match[4].replace(
                "{default_version_identifier}", "{DOCKER_VERSION}"
            )
            version = version.replace(
                "{DOCKER_VERSION}", settings.docker_version_effective or ""
            )

            full_image = f"{registry_url}/{image}:{version}"
            logger.debug("Found image: %s", full_image)

            image_dict[full_image] = {
                "docker_registry_url": registry_url,
                "docker_image": image,
                "docker_version": version,
            }

    logger.info("Found %d images to download", len(image_dict))
    return image_dict


def handle_files(settings: Settings) -> None:
    """
    Applies a file operation (copy or remove) on a temporary directory's contents.

    Based on the `action` setting, this function walks the `tmp_prefix` directory
    recursively and either copies files to `target_prefix` or removes them from there.
    Only specific top-level directories are allowed (`plugins`, `dags`, etc.)

    Args:
        settings (Settings): Configuration object specifying paths and action.

    Raises:
        SystemExit: If an unrecognized subdirectory is encountered.
    """
    logger.info("Applying action '%s' to files...", settings.action)
    tmp_dir = Path(settings.tmp_prefix)
    files = sorted(tmp_dir.rglob("*"), reverse=(settings.action == "remove"))

    for file_path in files:
        rel_path = file_path.relative_to(tmp_dir)
        if rel_path in {Path("."), Path("")}:
            logger.debug("Skipping root")
            continue

        if rel_path.parts[0] not in {
            "plugins",
            "dags",
            "mounted_scripts",
            "extensions",
        }:
            logger.error("Unknown relative directory: %s", rel_path)
            raise SystemExit(1)

        dest_path = Path(settings.target_prefix) / rel_path
        logger.info("Processing: %s -> %s", file_path, dest_path)

        if settings.action == "copy":
            if file_path.is_dir():
                dest_path.mkdir(parents=True, exist_ok=True)
            elif file_path.is_file():
                dest_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(file_path, dest_path)
            continue
        elif settings.action == "remove":
            if not dest_path.exists():
                logger.debug("Skip missing path during removal: %s", dest_path)
                continue

            if dest_path.is_file():
                try:
                    dest_path.unlink()
                    logger.debug("Removed file: %s", dest_path)
                except Exception as e:
                    logger.warning("Could not remove file %s: %s", dest_path, e)
                continue

            try:
                # only remove directory if it has no remaining visible files
                remaining = list(listdir_nohidden(dest_path, settings.target_prefix))
                if not remaining:
                    shutil.rmtree(dest_path)
                    logger.debug("Removed empty directory: %s", dest_path)
                else:
                    logger.debug("Skipped directory with remaining files: %s", dest_path)
            except FileNotFoundError:
                logger.debug("Directory already removed: %s", dest_path)
            except Exception as e:
                logger.warning("Error while removing directory %s: %s", dest_path, e)


def trigger_services(settings: Settings) -> None:
    """
    Triggers external services (Helm or Airflow) depending on the action.

    - If action is 'copy' or 'prefetch', it POSTs image data to the Helm API.
    - If action is 'remove', it POSTs to Airflow to notify DAG updates.

    Args:
        settings (Settings): Configuration object with API endpoints and image data.
    """
    if settings.action in {"copy", "prefetch"}:
        if not settings.helm_api:
            logger.warning("Skipping Helm API trigger: ADMIN_NAMESPACE not set.")
        else:
            logger.info("Triggering image pull via Helm API...")
            url = f"{settings.helm_api}/pull-docker-image"
            for _, payload in get_images(settings.tmp_prefix, settings).items():
                response = requests.post(url, json=payload)
                logger.info(
                    "Status: %d | Response: %s", response.status_code, response.text
                )

    if settings.action == "remove":
        if not settings.airflow_api:
            logger.warning("Skipping Airflow trigger: SERVICES_NAMESPACE not set.")
        else:
            logger.info("Triggering DAG update in Airflow...")
            response = requests.post(settings.airflow_api, json={})
            logger.info(
                "Status: %d | Response: %s", response.status_code, response.text
            )


def main() -> None:
    """
    Entrypoint for applying copy/remove/prefetch actions and triggering services.

    Loads and validates settings, performs file operations, and conditionally
    interacts with Helm and Airflow services based on environment configuration.
    """
    try:
        settings = Settings()
    except (ValidationError, ValueError) as e:
        logger.error("Configuration error:\n%s", e)
        raise SystemExit(1)

    handle_files(settings)
    logger.info("✓ Successfully applied action '%s' to all files", settings.action)

    if not settings.target_prefix.startswith("/kaapana/mounted/workflows"):
        logger.info("No workflow-related files to act on. Exiting.")
        return

    trigger_services(settings)

    if settings.action == "prefetch":
        logger.info("Running forever :)")
        while True:
            pass


if __name__ == "__main__":
    main()
