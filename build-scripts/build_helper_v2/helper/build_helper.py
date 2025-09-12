import hashlib
import json
import os
from typing import Set, TypeVar

import networkx as nx
from build_helper_v2.cli.selector import interactive_select
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container
from build_helper_v2.core.helm_chart import HelmChart
from build_helper_v2.helper.container_helper import ContainerHelper
from build_helper_v2.helper.helm_chart_helper import HelmChartHelper
from build_helper_v2.helper.issue_tracker import IssueTracker
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.utils.logger import get_logger
from InquirerPy import inquirer
from jinja2 import Environment, FileSystemLoader
from treelib.tree import Tree

T = TypeVar("T")  # HelmChart or Container
logger = get_logger()


class BuildHelper:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        """
        Initialize the ContainerHelper singleton with configuration and build state.

        Args:
            config (BuildConfig): Build configuration object.
            build_state (BuildState): Object managing container build state.
        """
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def get_platform_version(cls) -> str:
        """
        Get the platform version from the kaapana-admin-chart.

        Returns:
            str | None: Version string if found, else None
        """
        for chart in cls._build_state.charts_available:
            if chart.name == "kaapana-admin-chart":
                return chart.version  # or chart.app_version depending on your HelmChart
        logger.fatal("kaapana-admin-chart not found in charts_available")
        exit(1)

    @classmethod
    def report_unused_containers(cls):
        logger.debug("\nCollect unused containers:\n")
        unused_containers_json_path = (
            cls._build_config.build_dir / "build_containers_unused.json"
        )
        unused_containers = (
            cls._build_state.containers_available - cls._build_state.selected_containers
        )

        with open(unused_containers_json_path, "w") as fp:
            json.dump([c.to_dict() for c in unused_containers], fp, indent=4)

    @classmethod
    def report_image_stats(cls):
        image_stats = ContainerHelper.get_built_images_stats(cls.get_platform_version())

        logger.debug("\nCollect image stats:\n")
        image_stats_json_path = cls._build_config.build_dir / "image_stats.json"

        with open(image_stats_json_path, "w") as fp:
            json.dump(image_stats, fp, indent=4)

    @classmethod
    def report_used_base_images(cls):
        return NotImplemented

    @classmethod
    def report_available_containers(cls):
        logger.debug("\nCollect all containers:\n")
        built_containers_json_path = (
            cls._build_config.build_dir / "containers_available.json"
        )

        with open(built_containers_json_path, "w") as fp:
            json.dump(
                [c.to_dict() for c in cls._build_state.containers_available],
                fp,
                indent=4,
            )

    @classmethod
    def report_available_charts(cls):
        logger.debug("\nCollect all charts:\n")
        built_containers_json_path = (
            cls._build_config.build_dir / "charts_available.json"
        )

        with open(built_containers_json_path, "w") as fp:
            json.dump(
                [c.to_dict() for c in cls._build_state.charts_available],
                fp,
                indent=4,
            )

    @classmethod
    def report_unused_charts(cls):
        return NotImplemented

    @classmethod
    def generate_report(cls):
        BuildHelper.report_unused_containers()
        BuildHelper.report_used_base_images()
        BuildHelper.report_available_containers()
        BuildHelper.report_available_charts()
        BuildHelper.report_unused_charts()

        if cls._build_config.enable_image_stats:
            BuildHelper.report_image_stats()

    @classmethod
    def generate_build_graph(cls, platform_chart: HelmChart):
        build_graph = cls._build_graph(platform_chart)
        cls._build_state.build_graph = build_graph

    @classmethod
    def generate_build_tree(cls, platform_chart: HelmChart):
        build_tree_file = (
            cls._build_config.build_dir
            / platform_chart.name
            / f"tree-{platform_chart.name}.txt"
        )
        build_tree_file.parent.mkdir(parents=True, exist_ok=True)
        build_tree = cls._build_tree(platform_chart, include_containers=True)

        # Save tree to files
        build_tree.save2file(str(build_tree_file))
        logger.info(f"Build tree saved to: {build_tree_file}")
        for line in build_tree_file.read_text().splitlines():
            logger.info(line.strip())

    @classmethod
    def generate_deployment_script(
        cls,
        platform_chart: HelmChart,
    ):
        """
        Generate deployment script from platform parameters using Jinja2 template.
        """
        platform_config = {
            "platform_name": platform_chart.name,
            "platform_build_version": platform_chart.version,
            "container_registry_url": cls._build_config.default_registry,
        }
        if platform_chart.deployment_config:
            platform_config.update(platform_chart.deployment_config)
        if cls._build_config.include_credentials:
            platform_config.update(
                {
                    "container_registry_username": cls._build_config.registry_username,
                    "container_registry_password": cls._build_config.registry_password,
                }
            )

        file_loader = FileSystemLoader(cls._build_config.kaapana_dir / "platforms")
        env = Environment(loader=file_loader)
        template = env.get_template("deploy_platform_template.sh")

        output = template.render(**platform_config)
        deployment_script = (
            cls._build_config.build_dir / platform_chart.name / "deploy_platform.sh"
        )
        deployment_script.parent.mkdir(parents=True, exist_ok=True)

        with open(deployment_script, "w") as f:
            f.write(output)

        os.chmod(deployment_script, 0o775)
        logger.debug(f"Deployment script generated at {deployment_script}")

    @classmethod
    def get_platform_chart(cls) -> HelmChart:
        if len(cls._build_config.platform_filter) != 1:
            IssueTracker.generate_issue(
                component=cls.__name__,
                name=f"{cls._build_config.platform_filter}",
                msg=f"Platform Chart could not be determined from platform_filter: {cls._build_config.platform_filter}",
                level="FATAL",
            )
            exit(1)
        platform_chart = HelmChartHelper.get_chart(cls._build_config.platform_filter[0])
        if not platform_chart:
            IssueTracker.generate_issue(
                component=cls.__name__,
                name=f"{cls._build_config.platform_filter}",
                msg=f"Platform chart could not be determined from platform_filter: {cls._build_config.platform_filter}",
                level="FATAL",
            )
            exit(1)

        return platform_chart

    @classmethod
    def select_containers_to_build(cls):
        all_charts = cls._build_state.charts_available
        all_containers = cls._build_state.containers_available
        selected_chart_names = None
        selected_container_names = None

        if cls._build_config.interactive:
            # Step 1: choose Charts or Containers
            choice = inquirer.select(
                message="Do you want to select containers to build directly or by usage in charts?",
                choices=["Charts", "Containers"],
            ).execute()

            # Step 2: perform fuzzy multiselect
            if choice == "Charts":
                selected_chart_names = interactive_select(
                    [c.name for c in all_charts], "chart"
                )
            elif choice == "Containers":
                selected_container_names = interactive_select(
                    [c.image_name for c in all_containers], "container"
                )

        else:  # Non-interactive
            if cls._build_config.containers_to_build_by_charts:
                selected_chart_names = cls._build_config.containers_to_build_by_charts

            if cls._build_config.containers_to_build:
                selected_container_names = cls._build_config.containers_to_build

        # If any containers are specified, we do not resolve charts.
        if selected_container_names:
            containers = {
                ContainerHelper.get_container(name) for name in selected_container_names
            }
            cls._build_state.selected_containers = (
                ContainerHelper.collect_all_local_base_containers(containers)
            )
            return None

        G = cls._build_state.build_graph
        if selected_chart_names:
            containers_from_charts = set()
            charts = {
                chart
                for name in selected_chart_names
                if (chart := HelmChartHelper.get_chart(name)) is not None
            }
            for chart in charts:
                containers_from_chart = {
                    n for n in nx.descendants(G, chart) if isinstance(n, Container)
                }
                containers_from_charts.update(containers_from_chart)
        else:
            charts = cls._build_state.charts_available
            containers_from_charts = {
                n for n, _ in G.nodes(data=True) if isinstance(n, Container)
            }
        cls._build_state.selected_charts = charts
        cls._build_state.selected_containers = containers_from_charts

    @classmethod
    def collect_chart_containers(cls, chart: HelmChart) -> Set[Container]:
        containers: Set[Container] = set()
        visited_charts: Set[HelmChart] = set()

        def _collect(chart: HelmChart):
            if chart in visited_charts:
                return
            visited_charts.add(chart)

            # add chart's own containers
            containers.update(chart.chart_containers)

            # recurse into dependencies
            for dep in chart.chart_dependencies:
                _collect(dep)
            for coll in chart.kaapana_collections:
                _collect(coll)
            for ext in chart.preinstall_extensions:
                _collect(ext)

        _collect(chart)
        base_containers = ContainerHelper.collect_all_local_base_containers(containers)
        containers.update(base_containers)
        return containers

    @staticmethod
    def _build_graph(root_chart: HelmChart) -> nx.DiGraph:
        G = nx.DiGraph()
        visited = set()  # Track fully processed charts

        def add_chart(chart: HelmChart):
            if chart in visited:  # Only skip if fully processed
                return
            visited.add(chart)  # Mark as processed

            G.add_node(chart, type="chart")

            # Dependencies
            for dep in chart.chart_dependencies:
                G.add_edge(chart, dep, type="subchart")
                add_chart(dep)

            # Collections
            for coll in chart.kaapana_collections:
                G.add_edge(chart, coll, type="collection")
                add_chart(coll)

            # Containers
            for container in chart.chart_containers:
                G.add_node(container, type="container")
                G.add_edge(chart, container, type="produces")

                for base in container.base_images:
                    G.add_node(base, type="container")
                    G.add_edge(container, base, type="base-image")

        # Start recursion from root
        add_chart(root_chart)
        return G

    @staticmethod
    def _build_tree(root_chart: HelmChart, include_containers=False):
        """
        Generate a Tree() from a list of root charts.
        Optionally include containers and their base images.
        Guarantees unique node IDs using a hash of the full hierarchical path.
        Only include allowed root charts and skip runtime-only charts.
        """
        build_tree = Tree()
        build_tree.create_node("ROOT", "ROOT")

        def add_chart(chart: HelmChart, parent_tree_id: str, path_prefix=""):
            # Skip runtime-only charts
            if getattr(chart, "runtime_only", False):
                return

            # Full path for hashing
            current_path = f"{path_prefix}/{chart.name}"
            tree_id = BuildHelper.hash_id(current_path)
            build_tree.create_node(chart.name, tree_id, parent=parent_tree_id)

            # Add containers if requested
            if include_containers and getattr(chart, "chart_containers", None):
                containers_path = f"{current_path}/containers"
                containers_id = BuildHelper.hash_id(containers_path)
                build_tree.create_node("containers", containers_id, parent=tree_id)

                for container in chart.chart_containers:
                    container_path = (
                        f"{containers_path}/{container.image_name}:{container.version}"
                    )
                    c_id = BuildHelper.hash_id(container_path)
                    build_tree.create_node(container.tag, c_id, parent=containers_id)

                    # Base images
                    if getattr(container, "base_images", None):
                        base_path = f"{container_path}/base-images"
                        base_id = BuildHelper.hash_id(base_path)
                        build_tree.create_node("base-images", base_id, parent=c_id)
                        for base in container.base_images:
                            base_img_path = (
                                f"{base_path}/{base.image_name}:{base.version}"
                            )
                            base_img_id = BuildHelper.hash_id(base_img_path)
                            build_tree.create_node(
                                f"{base.image_name}:{base.version}",
                                base_img_id,
                                parent=base_id,
                            )

            # Recurse into sub-charts / dependencies
            if getattr(chart, "chart_dependencies", None):
                subcharts_path = f"{current_path}/sub-charts"
                subcharts_id = BuildHelper.hash_id(subcharts_path)
                build_tree.create_node("sub-charts", subcharts_id, parent=tree_id)
                for dep in chart.chart_dependencies:
                    add_chart(dep, subcharts_id, path_prefix=current_path)

        add_chart(root_chart, "ROOT")

        return build_tree

    @staticmethod
    def hash_id(path: str) -> str:
        """Generate a short SHA1 hash from a string."""
        return hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]
