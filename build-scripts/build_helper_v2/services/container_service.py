import os
import time
from dataclasses import dataclass
from glob import glob
from pathlib import Path
from queue import Empty, PriorityQueue
from shutil import which
from threading import Lock, Thread
from typing import Any, Dict, Set

from alive_progress import alive_bar
from build_helper_v2.cli.progress import ProgressBar, Result
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container, Status
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.command_helper import CommandHelper
from build_helper_v2.utils.logger import get_logger

logger = get_logger()


class ContainerService:
    # singleton-like class
    _config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, config: BuildConfig, build_state: BuildState):
        """Initialize the singleton with context."""
        if cls._config is None:
            cls._config = config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def verify_container_engine_installed(cls):
        logger.debug("")
        logger.debug(" -> Container Init")
        logger.debug(f"Container engine: {cls._config.container_engine}")

        if which(cls._config.container_engine) is None:
            logger.error(f"{cls._config.container_engine} was not found!")
            logger.error("Please install {Container.container_engine} on your system.")
            if cls._config.exit_on_error:
                exit(1)

    @classmethod
    def container_registry_login(cls, username: str, password: str):
        registry = cls._config.default_registry
        logger.info(f"-> Container registry-logout: {registry}")

        logout_cmd = [cls._config.container_engine, "logout", registry]

        CommandHelper.run(
            logout_cmd,
            logger=logger,
            timeout=10,
            context="registry-logout",
            exit_on_error=cls._config.exit_on_error,
        )
        logger.info(f"-> Container registry-login: {registry}")

        login_cmd = [
            cls._config.container_engine,
            "login",
            registry,
            "--username",
            username,
            "--password",
            password,
        ]
        CommandHelper.run(
            login_cmd,
            logger=logger,
            timeout=10,
            context="registry-login",
            exit_on_error=cls._config.exit_on_error,
        )

    @classmethod
    def collect_containers(cls) -> Set[Container]:
        logger.debug("")
        logger.debug(" collect_containers")

        dockerfiles_found = list(cls._config.kaapana_dir.rglob("Dockerfile*"))
        logger.info("")
        logger.info(f"-> Found {len(dockerfiles_found)} Dockerfiles @Kaapana")

        if (
            cls._config.external_source_dirs is not None
            and len(cls._config.external_source_dirs) > 0
        ):
            for external_source in cls._config.external_source_dirs:
                logger.info("")
                logger.info(f"-> adding external sources: {external_source}")
                external_dockerfiles_found = glob(
                    str(external_source) + "/**/Dockerfile", recursive=True
                )
                external_dockerfiles_found = [
                    path
                    for path in Path(external_source).rglob("Dockerfile")
                    if Path(cls._config.kaapana_dir)
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

        # Init Trivy if configuration check is enabled
        # if self.config.configuration_check:
        #     trivy_utils = self.trivy_utils
        #     trivy_utils.dockerfile_report_path = os.path.join(
        #         trivy_utils.reports_path, "dockerfile_reports"
        #     )
        #     os.makedirs(trivy_utils.dockerfile_report_path, exist_ok=True)

        dockerfiles_found = sorted(set(dockerfiles_found))

        if cls._config.configuration_check:
            bar_title = "Collect container and check configuration"
        else:
            bar_title = "Collect container"

        with alive_bar(len(dockerfiles_found), dual_line=True, title=bar_title) as bar:
            for dockerfile in dockerfiles_found:
                bar()
                if cls._config.build_ignore_patterns and any(
                    pattern in dockerfile.as_posix()
                    for pattern in cls._config.build_ignore_patterns
                ):
                    logger.debug(f"Ignoring Dockerfile {dockerfile}")
                    continue

                # Check Dockerfiles for configuration errors using Trivy
                # if self.config.configuration_check:
                #     trivy_utils.check_dockerfile(dockerfile)

                container = Container.from_dockerfile(
                    dockerfile, build_config=cls._config
                )
                bar.text(container.image_name)
                cls._build_state.add_container(container)

        cls.check_base_containers()

        return cls._build_state.container_images_available

    @classmethod
    def check_base_containers(cls):
        logger.debug("")
        logger.debug(" check_base_containers")
        logger.debug("")
        for container in cls._build_state.container_images_available:
            for base_image in container.base_images:
                if base_image.local_image and not any(
                    base_image.tag == available_container.tag
                    for available_container in cls._build_state.container_images_available
                ):
                    container.missing_base_images.append(base_image)
                    logger.error("")
                    logger.error(
                        f"-> {container.tag} - base_image missing: {base_image.tag}"
                    )
                    logger.error("")
                    if cls._config.exit_on_error:
                        exit(1)

    @classmethod
    def pull_container_image(cls, image_tag: str):
        command = [cls._config.container_engine, "pull", image_tag]
        logger.info(f"{image_tag}: Start pulling container image")

        CommandHelper.run(
            command,
            logger=logger,
            timeout=6000,
            env=dict(os.environ, DOCKER_BUILDKIT=f"{cls._config.enable_build_kit}"),
        )

    @classmethod
    def resolve_base_images_into_container(cls):
        """
        Replace local BaseImage references in each container base_images attribute
        with the actual Container objects.

        This method iterates over all containers in `container_images_available` and checks
        their `base_images` list. If a base image is marked as `local_image`, it is a base
        that is also being built locally. This function resolves it to the corresponding
        Container object from the build state, so that dependency checks can correctly
        use the Container's build status.

        After calling this method:
            - Local base images in `container.base_images` point to the actual Container objects.
            - Non-local base images remain as BaseImage references.
            - Dependency checks can safely inspect `container.base_images` to determine if all
            required containers are built.

        Raises:
            KeyError: If a local base image cannot be resolved to a known Container.
        """
        for c in cls._build_state.container_images_available:
            c.base_images = {
                (
                    cls.resolve_reference_to_container(
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
    def resolve_reference_to_container(
        cls, registry: str, image_name: str, version: str
    ) -> Container:
        """
        Resolves a container image reference found in a Helm chart (e.g., in values.yaml or templates)
        to a known Container object from the collected build state.

        This function searches the build state's available container images for a match based on
        the given registry and image name. If exactly one match is found, it is returned.
        If zero or multiple matches are found, a build issue is logged and reported.

        Args:
            registry (str): The container registry name (e.g., 'docker.io', 'ghcr.io').
            image_name (str): The image name without the tag (e.g., 'my-service').
            chart_id (str): The name of the Helm chart for logging and issue tracking.
            chartfile (Path): Path to the chart's Chart.yaml, used for issue context.

        Returns:
            Container: The resolved container object, if found unambiguously. Otherwise, returns None.
        """
        matches = [
            c
            for c in cls._build_state.container_images_available
            if c.image_name == image_name
            and c.registry == registry
            and c.version == version
        ]

        if len(matches) != 1:
            logger.error(
                f"{image_name}: expected 1 container for {registry}/{image_name}, found {len(matches)}"
            )
            for match in matches:
                logger.error(f"Dockerfile found: {match.dockerfile}")

            IssueTracker.generate_issue(
                component=ContainerService.__name__,
                name=f"{registry}/{image_name}:{version}",
                msg=f"Container not found or ambiguous: {image_name}",
                level="ERROR",
                path=str(),
            )

        container = matches[0]
        logger.debug(f"{image_name}: container found: {container.tag}")
        return container

    @staticmethod
    def all_dependencies_ready(container: Container) -> bool:
        """
        Check if all local base images of a container are built or unchanged.
        Non-local base images are ignored.
        """
        for b in container.base_images:
            if b.local_image:
                if not isinstance(b, Container):
                    return False
                if b.status not in {
                    Status.BUILT,
                    Status.NOTHING_CHANGED,
                    Status.PUSHED,
                }:
                    return False
        return True

    @classmethod
    def build_and_push_containers(cls, selected_containers: Set["Container"]):
        ready_queue = PriorityQueue()
        results: Dict[str, Result] = {}
        results_lock = Lock()
        failed_set = set()
        waiting_set = set(selected_containers)

        with results_lock:
            for c in selected_containers:
                results[c.tag] = Result(
                    tag=c.tag, status=str(c.status), build_time="-", push_time="-"
                )

        for c in list(waiting_set):
            if cls.all_dependencies_ready(c):
                priority = 0 if c.local_image else 1
                ready_queue.put((priority, c.tag, c))
                waiting_set.remove(c)

        def worker():
            nonlocal waiting_set
            while True:
                try:
                    _, _, container = ready_queue.get(timeout=1)
                except Empty:
                    if not waiting_set and ready_queue.empty():
                        return
                    continue
                container: Container
                tag = container.tag
                with results_lock:
                    results[tag].status = "Status.BUILDING"

                build_issue, build_duration = container.build(config=cls._config)
                with results_lock:
                    if build_issue:
                        build_issue.log_self(logger)
                        results[tag].status = str(container.status)
                        results[tag].build_time = "-"
                        failed_set.add(container)
                        ready_queue.task_done()
                    else:
                        results[tag].status = (
                            "Status.PUSHING" if not cls._config.build_only else "DONE"
                        )
                        results[tag].build_time = (
                            f"{build_duration:0.2f}s" if build_duration else "-"
                        )

                if not cls._config.build_only:
                    push_issue, push_duration = container.push(cls._config)
                    with results_lock:
                        if push_issue:
                            IssueTracker.issues.append(push_issue)
                            push_issue.log_self(logger)
                            results[tag].status = "PUSH_FAILED"
                            results[tag].push_time = "-"
                            failed_set.add(container)
                            ready_queue.task_done()
                        else:
                            results[tag].status = str(container.status)
                            results[tag].push_time = (
                                f"{push_duration:0.2f}s" if push_duration else "-"
                            )

                ready_queue.task_done()

                newly_ready = set()
                to_fail = set()
                for c in list(waiting_set):
                    if any(
                        isinstance(b, Container) and b in failed_set
                        for b in c.base_images
                    ):
                        with results_lock:
                            results[c.tag].status = "SKIPPED (failed base)"
                        failed_set.add(c)
                        to_fail.add(c)
                        continue

                    if cls.all_dependencies_ready(c):
                        priority = 0 if c.local_image else 1
                        ready_queue.put((priority, c.tag, c))
                        newly_ready.add(c)

                waiting_set -= newly_ready | to_fail

        threads = [Thread(target=worker) for _ in range(cls._config.parallel_processes)]

        with ProgressBar(
            total=len(selected_containers),
            title="Build-Container",
            results=results,
            use_rich=True,
        ) as pb:
            for t in threads:
                t.start()

            last_completed = 0
            while any(t.is_alive() for t in threads):
                with results_lock:
                    completed = sum(
                        1
                        for r in results.values()
                        if r.status
                        in {
                            "DONE",
                            "BUILD_FAILED",
                            "PUSH_FAILED",
                            "SKIPPED (failed base)",
                        }
                    )
                for _ in range(completed - last_completed):
                    pb.advance()
                last_completed = completed

                pb.refresh()
                time.sleep(0.2)

            for t in threads:
                t.join()
            pb.refresh()

        if waiting_set:
            remaining = [c.tag for c in waiting_set]
            logger.fatal(
                f"Containers could not be built (missing/cyclic dependencies): {remaining}"
            )

        return results

    # @classmethod
    # def get_images_stats(cls):
    #     images_stats = {}
    #     container_image_versions = set(
    #         [x.split(":")[-1] for x in cls._build_state.built_containers]
    #     )
    #     for container_image_version in container_image_versions:
    #         images_stats[container_image_version] = get_image_stats(
    #             version=container_image_version
    #         )
    #     return images_stats

    #         BuildUtils.logger.info("")
    #         BuildUtils.logger.info("")
    #         BuildUtils.logger.info("PLATFORM BUILD DONE.")
    #                 msg=f"There were too many build-rounds! Still missing: {waiting_containers_to_built}",
    #                 level="FATAL",
    #             )

    #         BuildUtils.logger.info("")
    #         BuildUtils.logger.info("")
    #         BuildUtils.logger.info("PLATFORM BUILD DONE.")

    @staticmethod
    def collect_all_local_base_containers(containers: set[Container]) -> set[Container]:
        """
        Recursively collect all local base-images that are also containers.
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
