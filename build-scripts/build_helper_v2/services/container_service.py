import os
from glob import glob
from pathlib import Path
from shutil import which
from subprocess import PIPE, run
from typing import List

from alive_progress import alive_bar
from build_helper_v2.core.app_context import AppContext
from build_helper_v2.models import Container
from build_helper_v2.services.report_service import ReportService
from build_helper_v2.utils.command_helper import CommandHelper


class ContainerService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.logger = ctx.logger
        self.config = ctx.config
        self.build_state = ctx.build_state

    def verify_container_engine_installed(self) -> None:
        self.logger.debug("")
        self.logger.debug(" -> Container Init")
        self.logger.debug(f"Container engine: {self.config.container_engine}")

        if which(self.config.container_engine) is None:
            self.logger.error(f"{self.config.container_engine} was not found!")
            self.logger.error(
                "Please install {Container.container_engine} on your system."
            )
            if self.config.exit_on_error:
                exit(1)

    def container_registry_login(self, username: str, password: str):
        registry = self.config.default_registry
        self.logger.info(f"-> Container registry-logout: {registry}")

        logout_cmd = [self.config.container_engine, "logout", registry]

        CommandHelper.run(
            logout_cmd,
            logger=self.logger,
            timeout=10,
            context="registry-logout",
            exit_on_error=self.config.exit_on_error,
            quiet=True,
        )
        self.logger.info(f"-> Container registry-login: {registry}")

        login_cmd = [
            self.config.container_engine,
            "login",
            registry,
            "--username",
            username,
            "--password",
            password,
        ]
        CommandHelper.run(
            login_cmd,
            logger=self.logger,
            timeout=10,
            context="registry-login",
            exit_on_error=self.config.exit_on_error,
            quiet=True,
        )

    def collect_containers(self) -> List[Container]:
        self.logger.debug("")
        self.logger.debug(" collect_containers")

        dockerfiles_found = list(self.config.kaapana_dir.rglob("Dockerfile*"))
        self.logger.info("")
        self.logger.info(f"-> Found {len(dockerfiles_found)} Dockerfiles @Kaapana")

        if (
            self.config.external_source_dirs is not None
            and len(self.config.external_source_dirs) > 0
        ):
            for external_source in self.config.external_source_dirs:
                self.logger.info("")
                self.logger.info(f"-> adding external sources: {external_source}")
                external_dockerfiles_found = glob(
                    str(external_source) + "/**/Dockerfile", recursive=True
                )
                external_dockerfiles_found = [
                    str(path)
                    for path in Path(external_source).rglob("Dockerfile")
                    if Path(self.config.kaapana_dir) not in path.parents
                ]
                dockerfiles_found.extend(external_dockerfiles_found)
                self.logger.info(f"Found {len(dockerfiles_found)} Dockerfiles")
                self.logger.info("")

        if len(dockerfiles_found) != len(set(dockerfiles_found)):
            self.logger.warning(
                f"-> Duplicate Dockerfiles found: {len(dockerfiles_found)} vs {len(set(dockerfiles_found))}"
            )
            for duplicate in set(
                [x for x in dockerfiles_found if dockerfiles_found.count(x) > 1]
            ):
                self.logger.warning(duplicate)
            self.logger.warning("")

        # Init Trivy if configuration check is enabled
        # if self.config.configuration_check:
        #     trivy_utils = self.trivy_utils
        #     trivy_utils.dockerfile_report_path = os.path.join(
        #         trivy_utils.reports_path, "dockerfile_reports"
        #     )
        #     os.makedirs(trivy_utils.dockerfile_report_path, exist_ok=True)

        dockerfiles_found = sorted(set(dockerfiles_found))

        if self.config.configuration_check:
            bar_title = "Collect container and check configuration"
        else:
            bar_title = "Collect container"

        with alive_bar(len(dockerfiles_found), dual_line=True, title=bar_title) as bar:
            for dockerfile in dockerfiles_found:
                bar()
                if self.config.build_ignore_patterns and any(
                    pattern in dockerfile.as_posix()
                    for pattern in self.config.build_ignore_patterns
                ):
                    self.logger.debug(f"Ignoring Dockerfile {dockerfile}")
                    continue

                # Check Dockerfiles for configuration errors using Trivy
                # if self.config.configuration_check:
                #     trivy_utils.check_dockerfile(dockerfile)

                container = Container.from_dockerfile(dockerfile, self.ctx)
                bar.text(container.image_name)
                self.build_state.container_images_available.append(container)

        self.check_base_containers()

        return self.build_state.container_images_available

    def check_base_containers(self):
        self.logger.debug("")
        self.logger.debug(" check_base_containers")
        self.logger.debug("")
        for container in self.build_state.container_images_available:
            for base_image in container.base_images:
                if base_image.local_image and not any(
                    base_image.tag == available_container.tag
                    for available_container in self.build_state.container_images_available
                ):
                    container.missing_base_images.append(base_image)
                    self.logger.error("")
                    self.logger.error(
                        f"-> {container.tag} - base_image missing: {base_image.tag}"
                    )
                    self.logger.error("")
                    if self.config.exit_on_error:
                        exit(1)

        return self.build_state.container_images_available

    def pull_container_image(self, image_tag: str):
        command = [self.config.container_engine, "pull", image_tag]
        self.logger.info(f"{image_tag}: Start pulling container image")

        CommandHelper.run(
            command,
            logger=self.logger,
            timeout=6000,
            env=dict(os.environ, DOCKER_BUILDKIT=f"{self.config.enable_build_kit}"),
            log_on_error=f"{image_tag}: Can't pull container...",
            log_on_success=f"{image_tag}: Success",
        )

    @staticmethod
    def resolve_reference_to_container(
        registry: str,
        image_name: str,
        chart_id: str,
        chartfile: Path,
        ctx: "AppContext",
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
            ctx (AppContext): The build context, including logger and collected containers.

        Returns:
            Container: The resolved container object, if found unambiguously. Otherwise, returns None.
        """
        matches = [
            c
            for c in ctx.build_state.container_images_available
            if c.image_name == image_name and c.registry == registry
        ]

        if len(matches) != 1:
            ctx.logger.error(
                f"{image_name}: expected 1 container for {registry}/{image_name}, found {len(matches)}"
            )
            for match in matches:
                ctx.logger.error(f"Dockerfile found: {match.dockerfile}")

            ReportService.generate_issue(
                component=ContainerService.__name__,
                name=chart_id,
                msg=f"Chart container not found or ambiguous: {image_name}",
                level="ERROR",
                path=str(chartfile.parent),
                ctx=ctx,
            )

        container = matches[0]
        ctx.logger.debug(f"{image_name}: container found: {container.tag}")
        return container
