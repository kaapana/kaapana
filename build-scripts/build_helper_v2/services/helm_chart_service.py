import shutil
from collections import Counter
from typing import List

import yaml
from alive_progress import alive_bar
from build_helper_v2.core.app_context import AppContext
from build_helper_v2.models.helm_chart import HelmChart
from build_helper_v2.models.platform_config import PlatformConfig
from build_helper_v2.services.report_service import ReportService
from build_helper_v2.utils.command_helper import CommandHelper
from build_helper_v2.utils.extras import get_image_stats
from build_helper_v2.utils.git_utils import GitUtils


class HelmChartService:
    def __init__(self, ctx: AppContext):
        self.ctx = ctx
        self.logger = ctx.logger
        self.config = ctx.config
        self.build_state = ctx.build_state

    def helm_registry_login(self, username, password):
        self.logger.info(f"-> Helm registry-logout: {self.config.default_registry}")
        logout_cmd = ["helm", "registry", "logout", self.config.default_registry]

        logout_result = CommandHelper.run(
            logout_cmd,
            logger=self.logger,
            timeout=10,
            context="helm-logout",
            quiet=True,
        )

        # Log only if logout failed for a reason other than "not logged in"
        if (logout_result.returncode != 0) and (
            "Error: not logged in" not in logout_result.stderr
        ):
            self.logger.info(
                f"Helm couldn't logout from registry: {self.config.default_registry} -> not logged in!"
            )

        self.logger.info(f"-> Helm registry-login: {self.config.default_registry}")
        login_cmd = [
            "helm",
            "registry",
            "login",
            self.config.default_registry.split("/")[0],
            "--username",
            username,
            "--password",
            password,
        ]

        login_result = CommandHelper.run(
            login_cmd,
            logger=self.logger,
            timeout=10,
            context="helm-login",
            quiet=True,
        )

        if login_result.returncode != 0:
            self.logger.error("Something went wrong!")
            self.logger.error(
                f"Helm couldn't login into registry: {self.config.default_registry}"
            )
            self.logger.error(f"Message: {login_result.stdout}")
            self.logger.error(f"Error:   {login_result.stderr}")

            ReportService.generate_issue(
                component=self.__class__.__name__,
                name="helm_registry_login",
                msg=f"Helm couldn't login registry {self.config.default_registry}",
                level="FATAL",
                output=login_result,
                ctx=self.ctx,
            )

    def verify_helm_installed(self):
        if shutil.which("helm") is None:
            self.logger.error("Helm is not installed!")
            self.logger.error("-> install curl 'sudo apt install curl'")
            self.logger.error("-> install helm 'sudo snap install helm --classic'!")
            self.logger.error(
                "-> install the kubeval 'helm plugin install https://github.com/instrumenta/helm-kubeval'"
            )
            exit(1)

        helm_kubeval_cmd = ["helm", "kubeval", "--help"]
        CommandHelper.run(
            helm_kubeval_cmd,
            logger=self.logger,
            exit_on_error=self.config.exit_on_error,
            timeout=5,
            context="helm-kubeval",
            hints=[
                "Helm kubeval is not installed correctly!",
                "Make sure Helm kubeval-plugin is installed!",
                "hint: helm plugin install https://github.com/instrumenta/helm-kubeval",
            ],
            quiet=True,
        )

    def collect_charts(self) -> List[HelmChart]:
        """
        Collects all Helm charts found in the main kaapana directory and any external source directories.
        Filters duplicates and applies ignore patterns, returning a list of HelmChart objects.
        """
        chart_files = list(self.config.kaapana_dir.rglob("Chart.yaml"))
        self.logger.info("")
        self.logger.info(f"Found {len(chart_files)} Charts in kaapana_dir")

        for source_dir in self.config.external_source_dirs:
            self.logger.info(f"\nSearching for Charts in: {source_dir}")
            external_charts = list(source_dir.rglob("Chart.yaml"))

            # Exclude charts that are already in the main kaapana_dir
            new_charts = [
                chart
                for chart in external_charts
                if self.config.kaapana_dir not in chart.parents
            ]
            chart_files.extend(new_charts)

        # Count occurrences
        chart_counts = Counter(chart_files)
        duplicated_charts = [
            chart for chart, count in chart_counts.items() if count > 1
        ]

        if len(duplicated_charts) > 0:
            self.logger.warning(
                f"-> Duplicate Charts found: {len(chart_files)} vs {len(set(chart_files))}"
            )
            for chart in duplicated_charts:
                self.logger.warning(chart)
            self.logger.warning("")

        # Sort charts: deeper paths first, then alphabetically
        chart_files = sorted(set(chart_files), key=lambda p: (-len(p.parents), str(p)))

        self.logger.info("")
        self.logger.info(f"--> Found {len(chart_files)} Charts across sources")
        self.logger.info("")
        self.logger.info("Generating Chart objects ...")
        self.logger.info("")

        charts_objects = []
        with alive_bar(len(chart_files), dual_line=True, title="Collect-Charts") as bar:
            for chart_file in chart_files:
                bar()
                if any(
                    pat in str(chart_file)
                    for pat in (self.config.build_ignore_patterns or [])
                ):
                    self.logger.debug(f"Ignoring chart {chart_file}")
                    continue

                chart = HelmChart.from_chartfile(chart_file, self.ctx)
                bar.text(chart.name)
                self.build_state.charts_available.append(chart)
                charts_objects.append(chart)

        return charts_objects

    def generate_platform_config(self, platform_chart: HelmChart) -> PlatformConfig:
        version, branch, _, timestamp = GitUtils.get_repo_info(
            platform_chart.chartfile.parent
        )
        build_version = "0.0.0-latest" if self.config.version_latest else version

        config = PlatformConfig(
            platform_name=platform_chart.name,
            platform_build_version=build_version,
            platform_repo_version=version,
            platform_build_branch=branch,
            platform_last_commit_timestamp=timestamp,
        )

        self.ctx.set_platform_config(platform_config=config)
        return config

    def resolve_dependencies(self, platform_chart: HelmChart):
        """
        Using the build_state.available_charts resolve name,version tuples into HelmChart objects.
        
        Verify and load chart dependencies from 'requirements.yaml'.

        For platform charts, also verifies associated collections and preinstall extensions.
        Updates `dependencies` and `dependencies_count_all` accordingly.

        Args:
            platform_chart (HelmChart): The platform chart being validated.
        """
        if platform_chart.kaapana_type == "platform":
            platform_chart.check_collections()
            platform_chart.check_preinstall_extensions()

        self.logger.debug(f"{platform_chart.name}: check_dependencies")
        # self.dependencies_count_all = 0

        requirements_file_path = platform_chart.chartfile.parent / "requirements.yaml"

        if not requirements_file_path.exists():
            self.logger.debug(f"{platform_chart.name}: -> No requirements.yaml found")
            return

        requirements_yaml = {}
        with open(str(requirements_file_path)) as f:
            requirements_yaml = yaml.safe_load(f)

        if (
            requirements_yaml == None
            or "dependencies" not in requirements_yaml
            or requirements_yaml["dependencies"] == None
        ):
            self.logger.debug(f"{platform_chart.name}: -> No dependencies defined")
            return

        # self.dependencies_count_all = len(requirements_yaml["dependencies"])

        dependencies = []
        for dependency in requirements_yaml["dependencies"]:
            dependency_version = f"{dependency['version']}"
            if dependency_version == "0.0.0":
                dependency_version = platform_chart.repo_version
            else:
                dependency_version = (
                    self.ctx.get_platform_config().platform_repo_version
                )

            dependency_name = f"{dependency['name']}"
            self.add_dependency_by_id(
                dependency_name=dependency_name,
                dependency_version=dependency_version,
            )

        self.logger.debug(
            f"{platform_chart.name}: found {len(platform_chart.chart_dependencies)}/ dependencies."
        )

        if len(self.dependencies) != self.dependencies_count_all:
            self.logger.error(
                f"{platform_chart.name}: check_dependencies failed! -> size self.dependencies vs dependencies_count_all"
            )
            ReportService.generate_issue(
                component=HelmChart.__name__,
                name=f"{platform_chart.name}",
                msg="chart check_dependencies failed! -> size self.dependencies vs dependencies_count_all",
                level="ERROR",
                path=platform_chart.chartfile.parent,
                ctx=self.ctx,
            )

    def build_platform(self, platform_chart: HelmChart):
        self.logger.info(f"-> Start platform-build for: {platform_chart.name}")

        self.platform_config = self.generate_platform_config(
            platform_chart=platform_chart
        )

        self.resolve_dependencies(platform_chart=platform_chart)

        HelmChart.create_platform_build_files(platform_chart=platform_chart)
        nx_graph = generate_build_graph(platform_chart=platform_chart)
        build_order = BuildUtils.get_build_order(build_graph=nx_graph)

        assert exists(platform_chart.build_chartfile)
        BuildUtils.logger.debug(f"creating chart package ...")
        platform_chart.make_package()
        platform_chart.push()
        BuildUtils.logger.info(f"{platform_chart.chart_id}: DONE")

        generate_deployment_script(platform_chart)

        BuildUtils.logger.info("")
        BuildUtils.logger.info("Start container build...")
        containers_to_built = []
        container_count = len(build_order)
        for i in range(0, container_count):
            container_id = build_order[i]
            container_to_build = [
                x
                for x in BuildUtils.container_images_available
                if x.tag == container_id
            ]
            if len(container_to_build) == 1:
                container_to_build = container_to_build[0]
                if (
                    container_to_build.local_image
                    and container_to_build.build_tag == None
                ):
                    container_to_build.build_tag = container_to_build.tag

                containers_to_built.append(container_to_build)
            else:
                BuildUtils.logger.error(
                    f"{container_id} could not be found in available containers!"
                )
                BuildUtils.generate_issue(
                    component=suite_tag,
                    name="container_build",
                    msg=f"{container_id} could not be found in available containers!",
                    level="FATAL",
                )
        containers_to_built_tmp = containers_to_built.copy()
        list_mid_index = len(containers_to_built) // 2
        for idx, container in enumerate(containers_to_built_tmp):
            org_list_idx = containers_to_built.index(container)
            local_base_image = False
            for base_image in container.base_images:
                if base_image.local_image:
                    local_base_image = True

            if container.local_image and not local_base_image:
                containers_to_built.insert(0, containers_to_built.pop(org_list_idx))

            elif container.local_image and local_base_image:
                containers_to_built.insert(
                    list_mid_index, containers_to_built.pop(org_list_idx)
                )

            elif not container.local_image and local_base_image:
                containers_to_built += [containers_to_built.pop(org_list_idx)]

        BuildUtils.logger.info("")
        BuildUtils.logger.info("")
        build_rounds = 0

        containers_to_built = [
            (x, containers_to_built[x]) for x in range(0, len(containers_to_built))
        ]
        waiting_containers_to_built = sorted(containers_to_built).copy()
        with alive_bar(container_count, dual_line=True, title="Container-Build") as bar:
            with ThreadPool(BuildUtils.parallel_processes) as threadpool:
                while (
                    len(waiting_containers_to_built) != 0
                    and build_rounds <= BuildUtils.max_build_rounds
                ):
                    build_rounds += 1
                    BuildUtils.logger.info("")
                    BuildUtils.logger.info(f"Build round: {build_rounds}")
                    BuildUtils.logger.info("")
                    tmp_waiting_containers_to_built = []
                    result_containers = threadpool.imap_unordered(
                        parallel_execute, waiting_containers_to_built
                    )
                    for (
                        queue_id,
                        result_container,
                        issue,
                        waiting,
                        build_time_needed,
                        push_time_needed,
                    ) in result_containers:
                        if waiting != None:
                            BuildUtils.logger.info(
                                f"{result_container.build_tag}: Base image {waiting} not ready yet -> waiting list"
                            )
                            tmp_waiting_containers_to_built.append(result_container)
                        else:
                            bar()
                            BuildUtils.logger.info(
                                f"{result_container.build_tag} - build: {build_time_needed} - push {push_time_needed} : DONE"
                            )
                            if issue != None:
                                # Close threadpool if error is fatal
                                if (
                                    BuildUtils.exit_on_error
                                    or issue["level"] == "FATAL"
                                ):
                                    threadpool.terminate()

                                bar.text(f"{result_container.tag}: ERROR")
                                BuildUtils.logger.info("")
                                BuildUtils.generate_issue(
                                    component=issue["component"],
                                    name=issue["name"],
                                    level=issue["level"],
                                    msg=issue["msg"],
                                    output=(
                                        issue["output"] if "output" in issue else None
                                    ),
                                    path=issue["path"] if "path" in issue else "",
                                )
                            else:
                                bar.text(f"{result_container.build_tag}: ok")

                    tmp_waiting_containers_to_built = [
                        (x, tmp_waiting_containers_to_built[x])
                        for x in range(0, len(tmp_waiting_containers_to_built))
                    ]
                    waiting_containers_to_built = tmp_waiting_containers_to_built.copy()

        if (
            build_rounds == BuildUtils.max_build_rounds
            and len(waiting_containers_to_built) > 0
        ):
            BuildUtils.generate_issue(
                component=suite_tag,
                name="container_build",
                msg=f"There were too many build-rounds! Still missing: {waiting_containers_to_built}",
                level="FATAL",
            )

        BuildUtils.logger.info("")
        BuildUtils.logger.info("")
        BuildUtils.logger.info("PLATFORM BUILD DONE.")

        if BuildUtils.create_offline_installation is True:

            OfflineInstallerHelper.generate_microk8s_offline_version(
                dirname(platform_chart.build_chart_dir)
            )
            images_tarball_path = join(
                dirname(platform_chart.build_chart_dir),
                f"{platform_chart.name}-{platform_chart.build_version}-images.tar",
            )
            OfflineInstallerHelper.export_image_list_into_tarball(
                image_list=successful_built_containers,
                images_tarball_path=images_tarball_path,
                timeout=4000,
            )
            BuildUtils.logger.info("Finished: Generating platform images tarball.")

    # def generate_platform_build_tree(self):
    #     for chart in self.build_state.charts_available:
    #         if chart.kaapana_type != "platform":
    #             continue
    #         if (
    #             self.config.platform_filter
    #             and chart.name not in self.config.platform_filter
    #         ):
    #             self.logger.debug(f"Skipped {chart.chart_id} -> platform_filter set!")
    #             continue

    #         self.logger.info(f"\n\nBuilding platform-chart: {chart.name}\n")
    #         self.build_platform(platform_chart=chart)

    #     self.generate_component_usage_info()

    def get_platform_charts_to_build(self) -> List[HelmChart]:
        """
        Identify platform charts that should be built.

        This method filters `self.build_state.charts_available` and returns only
        those charts whose `kaapana_type` is "platform". If `self.config.platform_filter`
        is set, only charts in that filter are included.

        Returns:
            list: A list of chart objects to be built as platform charts.
        """
        charts_to_build = []
        for chart in self.build_state.charts_available:
            if chart.kaapana_type == "platform":
                if (
                    self.config.platform_filter is not None
                    and chart.name not in self.config.platform_filter
                ):
                    self.logger.debug(f"Skipped {chart.name} -> platform_filter set!")
                    continue
                charts_to_build.append(chart)
        return charts_to_build

    def build_platform_charts(self, charts_to_build: List[HelmChart]):
        """
        Build a list of platform charts.

        Args:
            charts_to_build (list): List of chart objects to build.
        """
        for chart in charts_to_build:
            self.logger.info("\n\n")
            self.logger.info(f"Building platform-chart: {chart.name}\n")
            self.build_platform(platform_chart=chart)

    def get_images_stats(self):
        images_stats = {}
        container_image_versions = set(
            [x.split(":")[-1] for x in self.ctx.build_state.built_containers]
        )
        for container_image_version in container_image_versions:
            images_stats[container_image_version] = get_image_stats(
                version=container_image_version
            )
        return images_stats

    def generate_platform_build_tree(self):
        """
        Orchestrate the platform chart build process.

        This method:
        1. Selects all eligible platform charts using `get_platform_charts_to_build()`.
        2. Builds each chart using `build_platform_charts()`.
        3. Runs post-build tasks, such as generating component usage information.

        The resulting build sequence is based on the current build state and configuration.
        """
        charts_to_build = self.get_platform_charts_to_build()
        self.build_platform_charts(charts_to_build)
        if self.ctx.config.enable_image_stats:
            image_stats = self.get_images_stats()
        self.generate_component_usage_info()

    # def generate_platform_build_tree(self):
    #     charts_to_build = []
    #     for chart in self.build_state.charts_available:
    #         if chart.kaapana_type is not None and chart.kaapana_type == "platform":
    #             if (
    #                 self.config.platform_filter is not None
    #                 and chart.name not in self.config.platform_filter
    #             ):
    #                 self.logger.debug(f"Skipped {chart.name} -> platform_filter set!")
    #                 continue

    #             self.logger.info("")
    #             self.logger.info("")
    #             self.logger.info(f"Building platform-chart: {chart.name}")
    #             self.logger.info("")
    #             charts_to_build.append(chart)

    #             self.build_platform(platform_chart=chart)

    #     self.generate_component_usage_info()

    def generate_component_usage_info(self):
        unused_containers_json_path = join(
            BuildUtils.build_dir, "build_containers_unused.json"
        )
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect unused containers:")
        BuildUtils.logger.debug("")
        unused_container = []
        for container_id, container in BuildUtils.container_images_unused.items():
            BuildUtils.logger.debug(f"{container.tag}")
            unused_container.append(container.get_dict())
        with open(unused_containers_json_path, "w") as fp:
            json.dump(unused_container, fp, indent=4)

        base_images_json_path = join(BuildUtils.build_dir, "build_base_images.json")
        base_images = {}
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect base-images:")
        BuildUtils.logger.debug("")
        for base_image_tag, child_containers in BuildUtils.base_images_used.items():
            if base_image_tag not in base_images:
                base_images[base_image_tag] = {}
            BuildUtils.logger.debug(f"{base_image_tag}")
            for child_container in child_containers:
                if child_container.build_tag is not None:
                    child_tag = child_container.build_tag
                else:
                    child_tag = f"Not build: {child_container.tag}"

                if child_tag not in base_images[base_image_tag]:
                    base_images[base_image_tag][child_tag] = {}

        changed = True
        runs = 0
        base_images = dict(
            sorted(base_images.items(), reverse=True, key=lambda item: len(item[1]))
        )
        while changed and runs <= BuildUtils.max_build_rounds:
            runs += 1
            del_tags = []
            changed = False
            for base_image_tag, child_images in base_images.items():
                for child_image_tag, child_image in child_images.items():
                    if child_image_tag in base_images:
                        base_images[base_image_tag][child_image_tag] = base_images[
                            child_image_tag
                        ]
                        del_tags.append(child_image_tag)

            for del_tag in del_tags:
                del base_images[del_tag]
                changed = True

        base_images = dict(
            sorted(
                base_images.items(),
                reverse=True,
                key=lambda item: sum(len(v) for v in item[1].values()),
            )
        )
        with open(base_images_json_path, "w") as fp:
            json.dump(base_images, fp, indent=4)

        all_containers_json_path = join(
            BuildUtils.build_dir, "build_containers_all.json"
        )
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all containers present:")
        BuildUtils.logger.debug("")
        all_container = []
        for container in BuildUtils.container_images_available:
            BuildUtils.logger.debug(f"{container.tag}")
            all_container.append(container.get_dict())

        with open(all_containers_json_path, "w") as fp:
            json.dump(all_container, fp, indent=4)

        all_charts_json_path = join(BuildUtils.build_dir, "build_charts_all.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all charts present:")
        BuildUtils.logger.debug("")
        all_charts = []
        for chart in BuildUtils.charts_available:
            BuildUtils.logger.debug(f"{chart.chart_id}")
            all_charts.append(chart.get_dict())

        with open(all_charts_json_path, "w") as fp:
            json.dump(all_charts, fp, indent=4)

        unused_charts_json_path = join(BuildUtils.build_dir, "build_charts_unused.json")
        BuildUtils.logger.debug("")
        BuildUtils.logger.debug("Collect all charts present:")
        BuildUtils.logger.debug("")
        unused_charts = []
        for chart_id, chart in BuildUtils.charts_unused.items():
            BuildUtils.logger.debug(f"{chart.chart_id}")
            unused_charts.append(chart.get_dict())

        with open(unused_charts_json_path, "w") as fp:
            json.dump(unused_charts, fp, indent=4)

        if BuildUtils.enable_image_stats:
            container_image_stats_path = join(BuildUtils.build_dir, "image_stats.json")
            with open(container_image_stats_path, "w") as fp:
                json.dump(BuildUtils.images_stats, fp, indent=4)
