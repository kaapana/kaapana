from __future__ import annotations

import logging
from pathlib import Path
from typing import List

from build_helper_v2.models import BuildConfig, IssueTracker
from build_helper_v2.utils.git_utils import GitUtils


class BaseImage:
    """Represents a parsed base image reference (FROM ... in Dockerfile)."""

    def __init__(
        self,
        tag: str,
        registry: str,
        project: str,
        name: str,
        version: str,
        local_image: bool = False,
    ):
        self.tag = tag
        self.registry = registry
        self.project = project
        self.name = name
        self.version = version
        self.local_image = local_image

    def __repr__(self) -> str:
        return f"BaseImage(tag={self.tag!r}, registry={self.registry!r}, project={self.project!r}, name={self.name!r}, version={self.version!r}, local={self.local_image})"

    @classmethod
    def from_tag(cls, tag: str) -> BaseImage:
        if ":" not in tag:
            raise ValueError(f"{tag}: Missing version in base-image tag")

        path, version = tag.rsplit(":", 1)
        parts = path.split("/")

        local_image = "local-only" in path
        registry = project = name = None

        if local_image:
            registry = "local-only"
            project = ""
            name = parts[-1]
        else:
            match len(parts):
                case 1:
                    registry = "Dockerhub"
                    project = ""
                    name = parts[0]
                case 2:
                    registry = "Dockerhub"
                    project, name = parts
                case 3:
                    registry, project, name = parts
                case 4:
                    registry = parts[0]
                    project = f"{parts[1]}/{parts[2]}"
                    name = parts[3]
                case _:
                    raise ValueError(f"{tag}: Unrecognized base-image structure")

        return cls(
            tag=tag,
            registry=registry,
            project=project,
            name=name,
            version=version,
            local_image=local_image,
        )


class Container:
    """Represents a buildable container image derived from a Dockerfile."""

    def __init__(
        self,
        dockerfile: Path,
        registry: str,
        tag: str,
        image_name: str,
        repo_version: str,
        base_images: List[BaseImage],
        operator_containers: List[str],
        missing_base_images: List[BaseImage] | None = None,
        build_ignore: bool = False,
        local_image: bool = False,
    ):
        self.dockerfile = dockerfile
        self.registry = registry
        self.tag = tag
        self.image_name = image_name
        self.repo_version = repo_version

        self.base_images = base_images
        self.operator_containers = operator_containers
        self.missing_base_images = missing_base_images or []

        self.build_ignore = build_ignore
        self.local_image = local_image

    def __repr__(self) -> str:
        return f"Container(tag={self.tag!r}, image_name={self.image_name!r}, repo_version={self.repo_version!r}, local={self.local_image})"

    @classmethod
    def from_dockerfile(
        cls,
        dockerfile: Path,
        build_config: BuildConfig,
        logger: logging.Logger,
        issues_tracker: IssueTracker,
    ) -> "Container":
        if not dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile}")

        lines = dockerfile.read_text(encoding="utf-8").splitlines()
        registry = ""
        image_name = ""
        repo_version = ""
        build_ignore = False
        local_image = False
        base_images = []

        for line in lines:
            line = line.strip()
            if line.startswith("LABEL REGISTRY="):
                registry = cls._extract_label_value(line)
            elif line.startswith("LABEL IMAGE="):
                image_name = cls._extract_label_value(line)
            elif line.startswith("LABEL VERSION="):
                repo_version = cls._extract_label_value(line)
            elif line.startswith("LABEL BUILD_IGNORE="):
                val = cls._extract_label_value(line).lower()
                build_ignore = val in {"true", "yes", "1"}
            elif line.startswith("FROM") and "#ignore" not in line:
                base_tag = line.split("FROM", 1)[1].split()[0].strip().replace('"', "")
                base_img = BaseImage.from_tag(base_tag)
                base_images.append(base_img)

        # Determine registry and version
        if registry and "local-only" in registry:
            local_image = True
            repo_version = "latest"
        else:
            build_version, *_ = GitUtils.get_repo_info(dockerfile.parent)
            repo_version = build_version

        registry = registry or build_config.default_registry
        tag = (
            f"{registry}/{image_name}:{repo_version}"
            if image_name and repo_version
            else None
        )

        if not image_name or not repo_version:
            logger.debug(f"{dockerfile.parent}: could not extract container infos!")
            IssueTracker.generate_issue(
                component=cls.__name__,
                name=str(dockerfile.parent),
                msg="could not extract container infos!",
                level="ERROR",
                ctx=ctx,
            )
            if build_config.exit_on_error:
                exit(1)

        registry = registry or build_config.default_registry

        tag = f"{registry}/{image_name}:{repo_version}"

        operator_containers = cls.find_operator_images(
            dockerfile.parent, build_config.default_registry, repo_version
        )

        container = cls(
            tag=tag,
            dockerfile=dockerfile,
            base_images=base_images,
            registry=registry,
            image_name=image_name or "",
            repo_version=repo_version,
            build_ignore=build_ignore,
            local_image=local_image,
            operator_containers=operator_containers,
        )
        return container

    @classmethod
    def find_operator_images(
        cls, container_dir: Path, default_registry: str, repo_version: str
    ) -> List[str]:
        operator_containers = []
        python_files = container_dir.glob("**/*.py")

        for python_file in python_files:
            with python_file.open("r", encoding="utf-8") as f:
                for line in f:
                    # Removed backward compatibility default_registry vs DEFAULT_REGISTRY
                    # Removed backward compatibility kaapana_build_version vs KAAPANA_BUILD_VERSION
                    if (
                        "image=" in line
                        and "{DEFAULT_REGISTRY}" in line
                        and "{KAAPANA_BUILD_VERSION}" in line
                    ):
                        image_str = line.strip().split('"')[1].replace(" ", "")
                        image_str = image_str.replace(
                            "{KAAPANA_BUILD_VERSION}", repo_version
                        )
                        container_id = image_str.replace(
                            "{DEFAULT_REGISTRY}", default_registry
                        )
                        operator_containers.append(container_id)
                    break

        return operator_containers

    @staticmethod
    def _extract_label_value(line: str) -> str:
        return line.split("=", 1)[1].strip().strip('"').strip("'")
