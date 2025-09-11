import re
from pathlib import Path
from typing import Any, List, Optional

from pydantic import BaseModel, Field, model_validator

SUPPORTED_LOG_LEVELS = ["DEBUG", "INFO", "WARN", "ERROR"]


def validate_registry_name(registry: str) -> bool:
    """Validates the Docker registry format."""
    registry_pattern = re.compile(r"^[a-z0-9.-]+(?::[0-9]+)?$")
    full_registry_path = re.compile(
        r"^([a-z0-9.-]+(?::[0-9]+)?)/([a-z0-9._-]+(?:/[a-z0-9._-]+)*)$"
    )
    return bool(registry_pattern.match(registry) or full_registry_path.match(registry))


class BuildConfig(BaseModel):
    # Registry
    default_registry: str
    registry_username: str
    registry_password: str
    include_credentials: bool
    no_login: bool = False

    # Build Script
    build_dir: Path
    kaapana_dir: Path
    version_latest: bool = False
    container_engine: str
    exit_on_error: bool
    log_level: str
    enable_linting: bool
    enable_build_kit: bool = (
        True  # Docker BuildKit: https://docs.docker.com/develop/develop-images/build_enhancements/
    )
    parallel_processes: int
    max_build_rounds: int = 5
    max_push_retries: int = 30

    # Build Target
    interactive: bool = False
    build_only: bool
    containers_to_build_by_charts: List[str] = Field(default_factory=list)
    containers_to_build: List[str] = Field(default_factory=list)

    # Others
    http_proxy: Optional[str]
    push_to_microk8s: bool
    create_offline_installation: bool
    platform_filter: List[str] = Field(default_factory=list)
    external_source_dirs: List[Path] = Field(default_factory=list)
    build_ignore_patterns: List[str] = Field(default_factory=list)

    # Additional Details
    vulnerability_scan: bool
    vulnerability_severity_level: Optional[str]
    configuration_check: bool
    configuration_check_severity_level: Optional[str]
    enable_image_stats: bool
    create_sboms: bool
    check_expired_vulnerabilities_database: bool

    @model_validator(mode="before")
    @classmethod
    def preprocess_lists(cls, data: dict[str, Any]) -> dict[str, Any]:
        # Convert CSV strings to lists
        for field_name in [
            "platform_filter",
            "build_ignore_patterns",
            "containers_to_build_by_charts",
            "containers_to_build",
        ]:
            if field_name in data and isinstance(data[field_name], str):
                data[field_name] = [
                    x.strip() for x in data[field_name].split(",") if x.strip()
                ]

        if "external_source_dirs" in data and isinstance(
            data["external_source_dirs"], str
        ):
            data["external_source_dirs"] = [
                Path(x.strip())
                for x in data["external_source_dirs"].split(",")
                if x.strip()
            ]

        return data

    @model_validator(mode="after")
    def validate_all(self) -> "BuildConfig":
        # Validate default_registry format if build_only is False
        if self.default_registry and not self.build_only:
            validate_registry_name(self.default_registry)

        # Validate log_level
        if self.log_level not in SUPPORTED_LOG_LEVELS:
            raise ValueError(f"Unsupported log level: {self.log_level}")

        # Validate external_source_dirs existence
        for path in self.external_source_dirs:
            if not path.is_dir():
                raise ValueError(f"External source dir does not exist: {path}")

        # Validate platforms directory exists inside kaapana_dir
        platforms_dir = self.kaapana_dir / "platforms"
        if not platforms_dir.is_dir():
            raise ValueError(f"`platforms` directory not found in {self.kaapana_dir}")

        return self

    def log_self(self, logger):
        fields = self.model_dump(
            exclude={
                "registry_username",
                "registry_password",
                "include_credentials",
            }
        )
        for field_name, value in sorted(fields.items()):
            logger.info(f"{field_name}: {value}")
