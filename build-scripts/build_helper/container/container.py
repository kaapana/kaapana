from __future__ import annotations

import os
import subprocess
import time
from enum import Enum, auto
from pathlib import Path
from subprocess import PIPE, run
from typing import List, Optional, Set

from build_helper.build import BuildConfig, Issue, IssueTracker
from build_helper.utils import GitUtils, get_logger

logger = get_logger()


class Status(Enum):
    NOT_BUILT = auto()  # initial state|waiting for dependencies
    SKIPPED = auto()  # Container was intentionally skipped (e.g., build_ignore)
    BUILT_ONLY = (
        auto()
    )  # Containers that are BUILT and should not be pushed (local containers, build-only flag)
    BUILT = auto()  # build succeeded
    PUSHED = auto()  # push succeeded
    NOTHING_CHANGED = auto()  # build succeeded but no changes
    FAILED = auto()  # build failed

    # For the ProgressDashboard
    PUSHING = auto()  # currently pushing
    BUILDING = auto()  # currently building


class BaseImage:
    """Represents a parsed base image reference (FROM ... in Dockerfile)."""

    def __init__(
        self,
        tag: str,
        registry: str,
        project: str,
        image_name: str,
        version: str,
        local_image: bool = False,
    ):
        self.tag = tag
        self.registry = registry
        self.project = project
        self.image_name = image_name
        self.version = version
        self.local_image = local_image
        self.build_status = Status.NOT_BUILT

    def __repr__(self) -> str:
        return f"BaseImage(tag={self.tag!r}, registry={self.registry!r}, project={self.project!r}, name={self.image_name!r}, version={self.version!r}, local={self.local_image})"

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
            image_name=name,
            version=version,
            local_image=local_image,
        )


class Container:
    """Represents a buildable container image derived from a Dockerfile."""

    def __init__(
        self,
        dockerfile: Path,
        registry: str,
        image_name: str,
        version: str,
        tag: str,
        base_images: Set[BaseImage | Container],
        missing_base_images: List[BaseImage | Container] | None = None,
        build_ignore: bool = False,
        local_image: bool = False,
    ):
        self.dockerfile = dockerfile
        self.registry = registry
        self.tag = tag
        self.image_name = image_name
        self.version = version

        self.base_images = base_images
        self.missing_base_images = missing_base_images or []

        self.container_build_dir: Optional[Path] = (
            None  # kaapana-extension-collections needs access to the built helm charts/
        )
        self.build_ignore = build_ignore
        self.local_image = local_image
        self.status = Status.NOT_BUILT
        self.build_time: str | float = "-"
        self.push_time: str | float = "-"

    def __repr__(self) -> str:
        return f"Container(tag={self.tag!r}, image_name={self.image_name!r}, repo_version={self.version!r}, local={self.local_image})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Container):
            return False
        return self.tag == other.tag

    def __hash__(self) -> int:
        return hash(self.tag)

    def __lt__(self, other):
        if not isinstance(other, Container):
            return NotImplemented
        return self.tag.lower() < other.tag.lower()

    def to_dict(self) -> dict:
        """Return a serializable dict representation of the container."""
        return {
            "tag": self.tag,
            "image_name": self.image_name,
            "version": self.version,
            "status": str(self.status),
            "build_time": self.build_time,
            "push_time": self.push_time,
            "local_image": self.local_image,
            "base_images": [
                b.tag if isinstance(b, Container) else str(b) for b in self.base_images
            ],
        }

    @classmethod
    def from_dockerfile(
        cls,
        dockerfile: Path,
        build_config: BuildConfig,
    ) -> "Container":
        if not dockerfile.exists():
            raise FileNotFoundError(f"Dockerfile not found: {dockerfile}")

        lines = dockerfile.read_text(encoding="utf-8").splitlines()
        registry = ""
        image_name = ""
        repo_version = ""
        build_ignore = False
        local_image = False
        base_images: set[BaseImage | Container] = set()

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
                base_images.add(base_img)

        # Determine registry and version
        if registry and "local-only" in registry:
            local_image = True
            repo_version = "latest"
        elif build_config.version_latest:
            version_str, *_ = GitUtils.get_repo_info(dockerfile.parent)
            base = version_str.split("-")[0]
            repo_version = f"{base}-latest"
        else:
            repo_version, *_ = GitUtils.get_repo_info(dockerfile.parent)

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
            )
            if build_config.exit_on_error:
                exit(1)

        registry = registry or build_config.default_registry

        tag = f"{registry}/{image_name}:{repo_version}"

        container = cls(
            dockerfile=dockerfile,
            registry=registry,
            image_name=image_name or "",
            version=repo_version,
            tag=tag,
            base_images=base_images,
            build_ignore=build_ignore,
            local_image=local_image,
        )
        return container

    @staticmethod
    def _extract_label_value(line: str) -> str:
        return line.split("=", 1)[1].strip().strip('"').strip("'")

    def build(self, config: BuildConfig) -> Optional[Issue]:
        logger.debug(f"{self.tag}: start building ...")
        issue = None

        if self.build_ignore:
            self.status = Status.SKIPPED
            return issue

        if config.http_proxy is not None:
            command = [
                config.container_engine,
                "build",
                "--build-arg",
                f"http_proxy={config.http_proxy}",
                "--build-arg",
                f"https_proxy={config.http_proxy}",
                "-t",
                self.tag,
                "-f",
                str(self.dockerfile),
                ".",
            ]
        else:
            command = [
                config.container_engine,
                "build",
                "-t",
                self.tag,
                "-f",
                str(self.dockerfile),
                ".",
            ]
        start_time = time.time()
        output = run(
            command,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=6000,
            cwd=(
                self.container_build_dir
                if self.container_build_dir
                else self.dockerfile.parent
            ),
            env=dict(
                os.environ,
                DOCKER_BUILDKIT=f"{config.enable_build_kit}",
            ),
        )
        end_time = time.time()

        if output.returncode == 0:
            if "---> Running in" in output.stdout:
                self.status = Status.BUILT_ONLY if self.local_image else Status.BUILT
                logger.debug(f"{self.tag}: Build sucessful.")
            else:
                self.status = Status.NOTHING_CHANGED
                logger.debug(f"{self.tag}: Build sucessful - no changes.")
            self.build_time = end_time - start_time
            return issue

        else:
            self.status = Status.FAILED
            logger.error(f"{self.tag}: Build failed!")

            issue = IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.tag}",
                msg="container build failed!",
                level="ERROR",
                output=output,
                path=str(self.dockerfile.parent),
            )
            return issue

    def _push_to_microk8s(self, config: BuildConfig) -> Optional[Issue]:
        """
        Push the container to MicroK8s by piping `docker save` directly into `microk8s ctr image import`.
        """
        issue = None

        if self.tag.startswith("local-only"):
            logger.info(f"Skipping: Pushing {self.tag} to microk8s, due to local-only")
            self.status = Status.SKIPPED
            return issue

        logger.info(f"Pushing {self.tag} to microk8s via pipe")

        try:
            start_time = time.time()
            # docker save -> stdout
            cmd_save = [config.container_engine, "save", self.tag]
            # microk8s import <- stdin
            cmd_import = ["microk8s", "ctr", "image", "import", "-"]

            save_proc = subprocess.Popen(
                cmd_save, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            import_proc = subprocess.Popen(
                cmd_import,
                stdin=save_proc.stdout,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            save_proc.stdout.close()  # allow save_proc to get SIGPIPE if import_proc exits

            out, err = import_proc.communicate(timeout=9000)
            save_err = save_proc.stderr.read()
            save_proc.wait(timeout=1)
            end_time = time.time()
            self.push_time = end_time - start_time

            if import_proc.returncode != 0:
                logger.error(f"Microk8s image push failed {err or save_err}!")
                issue = IssueTracker.generate_issue(
                    component="Microk8s image push",
                    name=self.tag,
                    msg=f"Microk8s image push failed {err or save_err}!",
                    level="ERROR",
                    output=[err or save_err],
                    path=str(self.dockerfile.parent),
                )
                self.status = Status.FAILED
                return issue

            logger.debug(f"Successfully pushed {self.tag} to microk8s via pipe")

        except subprocess.TimeoutExpired:
            save_proc.kill()
            import_proc.kill()
            logger.error(f"Microk8s image push timed out for {self.tag}!")
            issue = IssueTracker.generate_issue(
                component="Microk8s image push",
                name=self.tag,
                msg=f"Microk8s image push timed out!",
                level="ERROR",
                output=[err or save_err],
                path=str(self.dockerfile.parent),
            )
        self.status = Status.PUSHED
        return issue

    def push(self, config: BuildConfig) -> Optional[Issue]:
        issue: Optional[Issue] = None
        duration: Optional[float] = None
        logger.debug(f"{self.tag}: in push()")

        if self.status not in {Status.BUILT, Status.NOTHING_CHANGED}:
            logger.warning(
                f"{self.tag}: Skipping push since image has not been built successfully!"
            )
            logger.warning(f"{self.tag}: container_build_status: {self.status}")
            IssueTracker.generate_issue(
                component=self.__class__.__name__,
                name=f"{self.tag}",
                msg=f"Push skipped -> image has not been built successfully! container_build_status: {self.status}",
                level="WARNING",
                path=self.dockerfile.parent,
            )

        if self.local_image:
            logger.debug(f"{self.tag}: Skipping push since image is local!")
            return issue

        if config.push_to_microk8s is True:
            logger.info(f"Pushing {self.tag} to microk8s")
            return self._push_to_microk8s(config)

        logger.debug(f"{self.tag}: start pushing! ")
        retries = 0
        command = [
            config.container_engine,
            "push",
            self.tag,
        ]
        while retries < config.max_push_retries:
            start_time = time.time()
            retries += 1
            output = run(
                command,
                stdout=PIPE,
                stderr=PIPE,
                universal_newlines=True,
                timeout=9000,
            )
            duration = time.time() - start_time

            # Stop retrying on success or immutable
            if output.returncode == 0:
                logger.debug(f"{self.tag}: pushed -> success")
                self.status = Status.PUSHED
                self.push_time = duration
                return issue

            if "configured as immutable" in output.stderr:
                logger.warning(f"{self.tag}: Container not pushed -> immutable!")
                self.status = Status.NOTHING_CHANGED
                self.push_time = duration
                issue = IssueTracker.generate_issue(
                    component=self.__class__.__name__,
                    name=self.tag,
                    msg="Container not pushed -> immutable!",
                    level="WARNING",
                    output=output,
                    path=self.dockerfile.parent,
                )
                return issue

        self.status = Status.FAILED
        component_name = self.__class__.__name__
        path = self.dockerfile.parent

        # Determine reason of PUSH FAILED
        if "read only mode" in output.stderr:
            level = "WARNING"
            msg = "Container not pushed -> read only mode!"
            logger.warning(f"{self.tag}: {msg}")
        elif "denied" in output.stderr:
            level = "ERROR"
            msg = "Container not pushed -> access denied!"
            logger.error(f"{self.tag}: {msg}")
        else:
            level = "ERROR"
            msg = "Container not pushed -> unknown reason!"
            logger.error(f"{self.tag}: {msg}")

        # Generate the issue once
        issue = IssueTracker.generate_issue(
            component=component_name,
            name=self.tag,
            msg=msg,
            level=level,
            output=output,
            path=path,
        )

        return issue
