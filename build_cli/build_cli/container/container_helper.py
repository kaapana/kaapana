import os
import tempfile
from pathlib import Path
from shutil import which
from subprocess import PIPE, run
from typing import Any, Dict, Optional, Set, TypeVar

from alive_progress import alive_bar
from build_cli.build import BuildConfig, BuildState, Issue, IssueTracker
from build_cli.container import Container
from build_cli.utils import CommandUtils, get_logger, should_ignore_path

logger = get_logger()
T = TypeVar("T")  # HelmChart or Container

BUILDX_BUILDER_NAME = "kaapana-buildx"


class ContainerHelper:
    """
    Singleton-like helper class responsible for managing container builds and
    interactions with container engines.

    Responsibilities:
        - Verify container engine installation
        - Login to container registries
        - Collect containers from source directories
        - Resolve base image dependencies
        - Gather statistics on built images
    """

    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        """
        Initialize the ContainerHelper singleton with configuration and build state.

        Args:
            build_config (BuildConfig): Build configuration object.
            build_state (BuildState): Object managing container build state.

        Notes:
            This must be called before any other method in this class is used.
            Initialization will only run once; subsequent calls are ignored.
        """
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def verify_container_engine_installed(cls):
        """
        Verify that the configured container engine is installed on the system.
        """
        logger.debug("")
        logger.debug(" -> Container Init")
        logger.debug(f"Container engine: {cls._build_config.container_engine}")

        if which(cls._build_config.container_engine) is None:
            logger.error(f"{cls._build_config.container_engine} was not found!")
            logger.error("Please install {Container.container_engine} on your system.")
            if cls._build_config.exit_on_error:
                exit(1)

    @classmethod
    def ensure_buildx_builder(cls):
        """
        Ensure the dedicated docker-container buildx builder exists, but only
        when this run actually needs it. Container.build() only touches
        BUILDX_BUILDER_NAME when config.cache_enabled (--cache-from/--cache-to)
        -- a plain run builds with `docker build` and never needs this builder
        at all, so skip creating/inspecting it entirely.
        """
        if not cls._build_config.cache_enabled:
            return
        if cls._build_config.container_engine != "docker":
            return

        logger.info(f"-> Ensuring buildx builder: {BUILDX_BUILDER_NAME}")

        inspect_result = CommandUtils.run(
            ["docker", "buildx", "inspect", BUILDX_BUILDER_NAME],
            logger=logger,
            timeout=15,
            context="buildx-inspect",
            quiet=True,
        )

        if inspect_result.returncode != 0:
            with tempfile.TemporaryDirectory() as tmp_dir:
                create_command = [
                    "docker",
                    "buildx",
                    "create",
                    "--name",
                    BUILDX_BUILDER_NAME,
                    "--driver",
                    "docker-container",
                    "--driver-opt",
                    "network=host",
                ]
                create_command.extend(cls._buildx_proxy_driver_opts())
                create_command.extend(cls._buildx_dns_config_opts(Path(tmp_dir)))

                CommandUtils.run(
                    create_command,
                    logger=logger,
                    timeout=60,
                    context="buildx-create",
                    exit_on_error=cls._build_config.exit_on_error,
                    hints=[
                        "Cache export (--cache-to) requires the docker-container driver."
                    ],
                )

    @classmethod
    def _buildx_proxy_driver_opts(cls) -> list:
        """
        Build --driver-opt env.* flags so the isolated docker-container
        builder inherits proxy settings, mirroring the --http-proxy value
        already used for --build-arg http_proxy/https_proxy in Container.build().

        Without this, the builder container has its own network namespace and
        does not automatically pick up the host's proxy, causing outbound
        requests (e.g. apk/apt package fetches) to fail even though a plain
        `docker build` on the host succeeds.
        """
        http_proxy = cls._build_config.http_proxy
        if not http_proxy:
            return []

        driver_opts = []
        for proxy_var in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY"):
            driver_opts.extend(["--driver-opt", f"env.{proxy_var}={http_proxy}"])

        # Forward the host's no_proxy so internal/registry traffic doesn't get
        # routed through the proxy as well; the CLI has no dedicated option for
        # this, so fall back to whatever is set in the calling shell.
        no_proxy = os.environ.get("no_proxy") or os.environ.get("NO_PROXY")
        if no_proxy:
            for no_proxy_var in ("no_proxy", "NO_PROXY"):
                driver_opts.extend(["--driver-opt", f"env.{no_proxy_var}={no_proxy}"])

        return driver_opts

    @classmethod
    def _resolve_dns_nameservers(cls) -> list:
        """
        Non-loopback nameservers from this process's own /etc/resolv.conf.

        Docker substitutes a real, reachable upstream nameserver into
        resolv.conf when it generates one for a regular (non
        --network=host) container -- which is how this process itself is
        normally started, e.g. inside the ci-base image -- so these
        addresses are exactly what BuildKit's sandboxed RUN namespace needs.
        A loopback nameserver (e.g. systemd-resolved's 127.0.0.53 stub) is
        filtered out: it only resolves within *this* namespace's own
        loopback, not the separate one BuildKit copies it into.
        """
        try:
            resolv_conf = Path("/etc/resolv.conf").read_text()
        except OSError:
            return []

        nameservers = []
        for line in resolv_conf.splitlines():
            parts = line.split()
            if (
                len(parts) == 2
                and parts[0] == "nameserver"
                and not parts[1].startswith("127.")
            ):
                nameservers.append(parts[1])
        return nameservers

    @classmethod
    def _buildx_dns_config_opts(cls, tmp_dir: Path) -> list:
        """
        Write a buildkitd config pinning DNS nameservers for the isolated
        docker-container builder, and return the --buildkitd-config flag
        pointing at it (or [] if no usable nameserver was found).

        Without this, RUN steps (e.g. apk/apt) can intermittently fail with
        "DNS: transient error (try again later)": BuildKit copies this
        host's /etc/resolv.conf verbatim into each RUN step's own network
        namespace, and a loopback nameserver there is dead on arrival even
        though it resolves fine in this namespace. A plain `docker build`
        doesn't hit this -- dockerd's embedded builder substitutes a real
        upstream nameserver automatically; BuildKit's own docker-container
        driver does not.
        """
        nameservers = cls._resolve_dns_nameservers()
        if not nameservers:
            return []

        config_path = tmp_dir / "buildkitd.toml"
        servers = ", ".join(f'"{ns}"' for ns in nameservers)
        config_path.write_text(f"[dns]\n  nameservers = [{servers}]\n")
        return ["--buildkitd-config", str(config_path)]

    @classmethod
    def container_registry_login(cls, username: str, password: str):
        """
        Logour and login to the default container registry.
        Args:
            username (str): Registry username.
            password (str): Registry password.
        """
        registry = cls._build_config.default_registry
        logger.info(f"-> Container registry-logout: {registry}")

        logout_cmd = [cls._build_config.container_engine, "logout", registry]

        CommandUtils.run(
            logout_cmd,
            logger=logger,
            timeout=10,
            context="registry-logout",
            exit_on_error=cls._build_config.exit_on_error,
            quiet=True,
        )
        logger.info(f"-> Container registry-login: {registry}")

        login_cmd = [
            cls._build_config.container_engine,
            "login",
            registry,
            "--username",
            username,
            "--password",
            password,
        ]
        CommandUtils.run(
            login_cmd,
            logger=logger,
            timeout=10,
            context="registry-login",
            exit_on_error=cls._build_config.exit_on_error,
        )

    @classmethod
    def collect_containers(cls) -> Set[Container]:
        """
        Collect all Dockerfiles and initialize Container objects.

        This searches the configured Kaapana directory and any external sources,
        filters duplicates, applies ignore patterns, and adds containers to
        the build state.

        Returns:
            Set[Container]: A set of containers representing collected Dockerfiles.

        Side Effects:
            Updates ``_build_state.containers_available``.
        """
        logger.debug("")
        logger.debug(" collect_containers")

        dockerfiles_found = list(cls._build_config.kaapana_dir.rglob("Dockerfile*"))
        logger.info("")
        logger.info(f"-> Found {len(dockerfiles_found)} Dockerfiles @Kaapana")

        if (
            cls._build_config.external_source_dirs is not None
            and len(cls._build_config.external_source_dirs) > 0
        ):
            for external_source in cls._build_config.external_source_dirs:
                logger.info("")
                logger.info(f"-> adding external sources: {external_source}")
                external_dockerfiles_found = [
                    path
                    for path in Path(external_source).rglob("Dockerfile")
                    if Path(cls._build_config.kaapana_dir)
                    not in path.parents  # TODO Why filter here?
                ]
                dockerfiles_found.extend(external_dockerfiles_found)
                logger.info(f"Found {len(dockerfiles_found)} Dockerfiles")
                logger.info("")

        if len(dockerfiles_found) != len(set(dockerfiles_found)):
            logger.warning(
                f"-> Duplicate Dockerfiles found: {len(dockerfiles_found)} vs {len(set(dockerfiles_found))}"
            )
            for duplicate in set(
                [x for x in dockerfiles_found if dockerfiles_found.count(x) > 1]
            ):
                logger.warning(duplicate)
            logger.warning("")

        dockerfiles_found = sorted(set(dockerfiles_found))

        with alive_bar(
            len(dockerfiles_found), dual_line=True, title="Collect container"
        ) as bar:
            for dockerfile in dockerfiles_found:
                bar()
                if should_ignore_path(
                    dockerfile, cls._build_config.build_ignore_patterns
                ):
                    logger.debug(f"Ignoring Dockerfile {dockerfile}")
                    continue

                container = Container.from_dockerfile(
                    dockerfile, build_config=cls._build_config
                )
                bar.text(container.image_name)
                cls._build_state.add_container(container)

        cls.check_base_containers()

        return cls._build_state.containers_available

    @classmethod
    def check_base_containers(cls):
        """
        Verify that all local base images required by containers are present.
        """
        logger.debug("")
        logger.debug(" check_base_containers")
        logger.debug("")
        for container in cls._build_state.containers_available:
            for base_image in container.base_images:
                if base_image.local_image and not any(
                    base_image.tag == available_container.tag
                    for available_container in cls._build_state.containers_available
                ):
                    container.missing_base_images.append(base_image)
                    logger.error("")
                    logger.error(
                        f"-> {container.tag} - base_image missing: {base_image.tag}"
                    )
                    logger.error("")
                    if cls._build_config.exit_on_error:
                        exit(1)

    @classmethod
    def pull_container_image(cls, image_tag: str, platform: Optional[str] = None):
        """
        Pull a container image from a remote registry.

        Args:
            image_tag (str): Tag of the container image to pull.
            platform (Optional[str]): Platform for the container image.
        """

        command = [cls._build_config.container_engine, "pull"]
        if platform:
            command += ["--platform", platform]
        command.append(image_tag)
        logger.info(f"{image_tag}: Start pulling container image")

        CommandUtils.run(
            command,
            logger=logger,
            timeout=6000,
            env=dict(
                os.environ, DOCKER_BUILDKIT=f"{cls._build_config.enable_build_kit}"
            ),
        )

    @classmethod
    def resolve_base_images_into_container(cls):
        """
        Replace local BaseImage references in containers with actual Container objects.
        """
        for c in cls._build_state.containers_available:
            c.base_images = {
                (
                    cls.get_container(
                        registry=b.registry,
                        image_name=b.image_name,
                        version=b.version,
                    )
                    if b.local_image
                    else b
                )
                for b in c.base_images
            }

    @classmethod
    def get_container(
        cls,
        image_name: str,
        registry: Optional[str] = None,
        version: Optional[str] = None,
    ) -> Container:
        """
        Resolve a container reference to a collected Container object.

        Args:
            registry (str): Registry name.
            image_name (str): Image name.
            version (str): Version or tag of the image.

        Returns:
            Container: Resolved container object.
        """

        matches = [
            c
            for c in cls._build_state.containers_available
            if c.image_name == image_name
            and (registry is None or c.registry == registry)
            and (version is None or c.version == version)
        ]

        if len(matches) != 1:
            logger.error(
                f"{image_name}: expected 1 container for {registry}/{image_name}, found {len(matches)}"
            )
            for match in matches:
                logger.error(f"Dockerfile found: {match.dockerfile}")

            IssueTracker.generate_issue(
                component=ContainerHelper.__name__,
                name=f"{registry}/{image_name}:{version}",
                msg=f"Container not found or ambiguous: {image_name}",
                level="ERROR",
                path=str(),
            )

        container = matches[0]
        logger.debug(f"{image_name}: container found: {container.tag}")
        return container

    @classmethod
    def get_built_images_stats(cls, version: str) -> Dict[str, Dict[str, Any]]:
        """
        Collect statistics of container images matching a specified version.

        Combines data from `docker image ls` and `docker system df -v` to compute
        image size, unique/shared storage, build time, and number of containers using the image.

        Args:
            version (str): Version string to filter images.

        Returns:
            Dict[str, Dict[str, Any]]: Mapping from image tag to statistics dictionary.
        """
        images_stats: Dict[str, Dict[str, Any]] = {}
        command = [f"{cls._build_config.container_engine} image ls | grep {version}"]
        output = run(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=5,
        )
        if output.returncode == 0:
            system_df_output = output.stdout.split("\n")
            for image_stats in system_df_output:
                if len(image_stats) == 0:
                    continue
                image_name, image_tag, _, image_build_time, size_str = [
                    x for x in image_stats.strip().split("  ") if x != ""
                ]
                size = cls.convert_size(size_str)
                images_stats[f"{image_name}:{image_tag}"] = {"size": size}

        command = [
            f"{cls._build_config.container_engine} system df -v | grep {version}"
        ]
        output = run(
            command,
            shell=True,
            stdout=PIPE,
            stderr=PIPE,
            universal_newlines=True,
            timeout=120,
        )
        if output.returncode == 0:
            system_df_output = output.stdout.split("\n")
            for image_stats in system_df_output:
                if len(image_stats) == 0:
                    continue
                (
                    image_name,
                    image_tag,
                    _,
                    image_build_time,
                    size_str,
                    shared_size_str,
                    unique_size_str,
                    containers,
                ) = [x for x in image_stats.strip().split("  ") if x != ""]
                size = cls.convert_size(size_str)
                shared_size = cls.convert_size(shared_size_str)
                unique_size = cls.convert_size(unique_size_str)

                images_stats[f"{image_name}:{image_tag}"] = {
                    "size": size,
                    "unique_size": unique_size,
                    "shared_size": shared_size,
                    "image_build_time": image_build_time,
                    "containers": int(containers.strip()),
                }

        images_stats = {
            k: v
            for k, v in sorted(
                images_stats.items(),
                key=lambda item: item[1]["size"],
                reverse=True,
            )
        }
        return images_stats

    @staticmethod
    def convert_size(size_string: str) -> Optional[float]:
        """
        Convert a human-readable size string (e.g., '2.5GB', '500MB') to float GB.

        Args:
            size_string (str): Size string to convert.

        Returns:
            float | None: Converted size in GB, or None if unknown format.
        """
        if "GB" in size_string:
            return float(size_string.replace("GB", ""))
        elif "MB" in size_string:
            return round(float(size_string.replace("MB", "")) / 1000, 2)
        elif "kB" in size_string:
            return 0
        elif "B" in size_string:
            return 0
        else:
            return None

    @staticmethod
    def collect_all_local_base_containers(containers: set[Container]) -> set[Container]:
        """
        Recursively collect all local base images that are also containers.
        That means they are part of our codebase - local containers that need to be built,
        like: base-python-cpu, and not docker.io containers ubuntu:24.04

        Args:
            containers (set[Container]): Initial set of containers.

        Returns:
            set[Container]: Set including all local base containers.
        """
        all_containers = set(containers)
        queue = list(containers)

        while queue:
            container = queue.pop()
            for base in container.base_images:
                if isinstance(base, Container) and base not in all_containers:
                    all_containers.add(base)
                    queue.append(base)

        return all_containers


###################################################################################
# Internal helper classes for build coordination
###################################################################################


from dataclasses import dataclass
from enum import Enum, auto
from queue import Queue
from typing import Optional


class BuildEventType(Enum):
    STARTED = auto()
    BUILT = auto()
    PUSHED = auto()
    SKIPPED = auto()
    FAILED = auto()
    FINISHED = auto()


@dataclass(frozen=True)
class BuildEvent:
    """
    Immutable event emitted by workers.
    """

    type: BuildEventType
    container: Container
    issue: Optional[Issue] = None
    error: Optional[Exception] = None


EventQueue = Queue[BuildEvent]
