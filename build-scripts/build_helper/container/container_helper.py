import fnmatch
import os
import time
from pathlib import Path
from queue import Empty, PriorityQueue
from shutil import which
from subprocess import PIPE, run
from threading import Lock, Thread
from typing import Any, Dict, Optional, Set, TypeVar

from alive_progress import alive_bar

from build_helper.build import BuildConfig, BuildState, IssueTracker
from build_helper.cli.progress import ProgressBar
from build_helper.container import Container, Status
from build_helper.utils import CommandUtils, get_logger

logger = get_logger()
T = TypeVar("T")  # HelmChart or Container


class ContainerHelper:
    """
    Singleton-like helper class responsible for managing container builds and
    interactions with container engines.

    Responsibilities:
        - Verify container engine installation
        - Login to container registries
        - Collect containers from source directories
        - Resolve base image dependencies
        - Build and push containers in parallel
        - Track build statuses
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
                if cls._build_config.build_ignore_patterns and any(
                    fnmatch.fnmatch(dockerfile.as_posix(), pattern)
                    for pattern in cls._build_config.build_ignore_patterns
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
    def pull_container_image(cls, image_tag: str):
        """
        Pull a container image from a remote registry.

        Args:
            image_tag (str): Tag of the container image to pull.
        """

        command = [cls._build_config.container_engine, "pull", image_tag]
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
    def build_and_push_containers(cls) -> None:
        """
        Build and push all selected containers in parallel while respecting dependencies.

        Containers are processed in multiple threads. Containers with no pending dependencies
        are added to a ready queue. Each worker thread picks a container from the queue, builds it,
        pushes it (if applicable), updates dependent containers, and tracks build status.

        Side Effects:
            Updates container statuses in `cls._build_state.selected_containers`.
            Appends build or push issues to `IssueTracker.issues`.
            Logs progress to the console via `ProgressBar`.

        Raises:
            Logs fatal error if any containers remain unbuilt due to missing or cyclic dependencies.
        """
        ready_queue: PriorityQueue = PriorityQueue()
        waiting_set = set(cls._build_state.selected_containers)
        containers_lock = Lock()

        cls._initialize_ready_queue(waiting_set, ready_queue)

        def worker(pb: "ProgressBar") -> None:
            while True:
                try:
                    container: "Container" = ready_queue.get(timeout=1)[1]
                except Empty:
                    if not waiting_set and ready_queue.empty():
                        return
                    continue

                cls._process_container(
                    container,
                    waiting_set,
                    ready_queue,
                    containers_lock,
                    pb,
                )

                ready_queue.task_done()

        threads = []

        with ProgressBar(
            total=len(cls._build_state.selected_containers),
            title="Build-Container",
            containers=cls._build_state.selected_containers,
            use_rich=False,
        ) as pb:
            # Start threads
            for _ in range(cls._build_config.parallel_processes):
                t = Thread(target=worker, args=(pb,))
                t.start()
                threads.append(t)

            # Wait threads and refresh progress bar
            while any(t.is_alive() for t in threads):
                pb.refresh()
                time.sleep(0.2)

            for t in threads:
                t.join()

            pb.refresh(clear=True)

        if waiting_set:
            remaining = [c.tag for c in waiting_set]
            logger.fatal(
                f"Containers could not be built (missing/cyclic dependencies): {remaining}"
            )

    @classmethod
    def _initialize_ready_queue(
        cls, waiting_set: set, ready_queue: PriorityQueue
    ) -> None:
        """
        Populate the ready queue with containers that have all dependencies satisfied.

        Args:
            waiting_set (set): Set of containers pending build.
            ready_queue (PriorityQueue): Queue to store containers ready for processing.

        Side Effects:
            Removes ready containers from `waiting_set` and adds them to `ready_queue`.
        """
        for c in list(waiting_set):
            if cls.all_dependencies_ready(c):
                priority = 0 if c.local_image else 1
                ready_queue.put((priority, c))
                waiting_set.remove(c)

    @classmethod
    def _update_dependents(cls, waiting_set: set, ready_queue: PriorityQueue) -> None:
        """
        Move dependent containers to the ready queue or mark them as failed.

        A dependent container is added to the ready queue if all its base images are ready.
        If any base image has failed, the container is marked as failed and removed from waiting.

        Args:
            waiting_set (set): Set of containers still waiting to be processed.
            ready_queue (PriorityQueue): Queue for ready-to-build containers.

        Side Effects:
            Updates statuses of dependent containers.
            Modifies `waiting_set` by removing processed containers.
        """
        newly_ready = set()
        to_fail = set()
        for c in list(waiting_set):
            if any(
                isinstance(b, Container) and b.status == Status.FAILED
                for b in c.base_images
            ):
                c.status = Status.FAILED
                to_fail.add(c)
            elif cls.all_dependencies_ready(c):
                priority = 0 if c.local_image else 1
                ready_queue.put((priority, c))
                newly_ready.add(c)
        waiting_set -= newly_ready | to_fail

    @classmethod
    def _process_container(
        cls,
        container: "Container",
        waiting_set: set,
        ready_queue: PriorityQueue,
        containers_lock: Lock,
        pb: "ProgressBar",
    ) -> None:
        """
        Build and push a single container, updating progress and dependents.

        Steps:
            1. Build the container.
            2. Handle build issues or skipped status.
            3. Push the container if applicable.
            4. Update dependents based on build outcome.
            5. Update the progress bar.

        Args:
            container (Container): Container to build and push.
            waiting_set (set): Containers still waiting to be built.
            ready_queue (PriorityQueue): Queue of containers ready for processing.
            containers_lock (Lock): Thread lock to synchronize shared data.
            pb (ProgressBar): Progress bar to track container build progress.

        Side Effects:
            Updates container status.
            Logs build and push progress.
            Updates dependent containers in `waiting_set` and `ready_queue`.
            Appends issues to `IssueTracker.issues` if build or push fails.
        """

        build_issue = container.build(config=cls._build_config)

        with containers_lock:
            final_status = None

            if build_issue:
                IssueTracker.issues.append(build_issue)
                final_status = Status.FAILED
            elif container.status in {
                Status.SKIPPED,
                Status.BUILT_ONLY,
            }:
                final_status = container.status
            elif cls._build_config.build_only:
                final_status = Status.BUILT_ONLY

            if final_status:
                pb.finished_print(title="Finished", last_processed_container=container)
                pb.advance(last_processed_container=container, advance=1)
                cls._update_dependents(waiting_set, ready_queue)
                return

        push_issue = container.push(cls._build_config)
        with containers_lock:
            if push_issue:
                IssueTracker.issues.append(push_issue)

            pb.finished_print(title="Finished", last_processed_container=container)
            pb.advance(last_processed_container=container, advance=1)
            cls._update_dependents(waiting_set, ready_queue)

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

    @staticmethod
    def all_dependencies_ready(container: Container) -> bool:
        """
        Check if all local base images for a container are built or unchanged.

        Args:
            container (Container): Container to check.

        Returns:
            bool: True if all local dependencies are ready, False otherwise.
        """
        for b in container.base_images:
            if b.local_image:
                # Online reference ubuntu:24.04
                if not isinstance(b, Container):
                    return False
                if b.status not in {
                    Status.BUILT,
                    Status.BUILT_ONLY,
                    Status.NOTHING_CHANGED,
                    Status.PUSHED,
                    Status.SKIPPED,
                    Status.FAILED,
                }:
                    return False
        return True
