import hashlib
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import List, Set

import networkx as nx
import yaml
from alive_progress import alive_bar
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.helm_chart import HelmChart, KaapanaType
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.command_helper import CommandHelper
from build_helper_v2.utils.logger import get_logger
from jinja2 import Environment, FileSystemLoader
from treelib import Tree

logger = get_logger()


class HelmChartService:
    # singleton-like class
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        """Initialize the singleton with context."""
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def helm_registry_login(cls, username, password):
        logger.info(f"-> Helm registry-logout: {cls._build_config.default_registry}")
        logout_cmd = ["helm", "registry", "logout", cls._build_config.default_registry]

        logout_result = CommandHelper.run(
            logout_cmd,
            logger=logger,
            timeout=10,
            context="helm-logout",
        )

        # Log only if logout failed for a reason other than "not logged in"
        if (logout_result.returncode != 0) and (
            "Error: not logged in" not in logout_result.stderr
        ):
            logger.info(
                f"Helm couldn't logout from registry: {cls._build_config.default_registry} -> not logged in!"
            )

        logger.info(f"-> Helm registry-login: {cls._build_config.default_registry}")
        login_cmd = [
            "helm",
            "registry",
            "login",
            cls._build_config.default_registry.split("/")[0],
            "--username",
            username,
            "--password",
            password,
        ]

        login_result = CommandHelper.run(
            login_cmd,
            logger=logger,
            timeout=10,
            context="helm-login",
        )

        if login_result.returncode != 0:
            logger.error("Something went wrong!")
            logger.error(
                f"Helm couldn't login into registry: {cls._build_config.default_registry}"
            )
            logger.error(f"Message: {login_result.stdout}")
            logger.error(f"Error:   {login_result.stderr}")

            IssueTracker.generate_issue(
                component=cls.__name__,
                name="helm_registry_login",
                msg=f"Helm couldn't login registry {cls._build_config.default_registry}",
                level="FATAL",
                output=login_result,
            )

    @classmethod
    def verify_helm_installed(cls):
        if shutil.which("helm") is None:
            logger.error("Helm is not installed!")
            logger.error("-> install curl 'sudo apt install curl'")
            logger.error("-> install helm 'sudo snap install helm --classic'!")
            logger.error(
                "-> install the kubeval 'helm plugin install https://github.com/instrumenta/helm-kubeval'"
            )
            exit(1)

        helm_kubeval_cmd = ["helm", "kubeval", "--help"]
        CommandHelper.run(
            helm_kubeval_cmd,
            logger=logger,
            exit_on_error=cls._build_config.exit_on_error,
            timeout=5,
            context="helm-kubeval",
            hints=[
                "Helm kubeval is not installed correctly!",
                "Make sure Helm kubeval-plugin is installed!",
                "hint: helm plugin install https://github.com/instrumenta/helm-kubeval",
            ],
        )

    @classmethod
    def collect_charts(cls) -> Set[HelmChart]:
        """
        Collects all Helm charts found in the main kaapana directory and any external source directories.
        Filters duplicates and applies ignore patterns, returning a list of HelmChart objects.
        """
        chart_files = set(
            f
            for f in cls._build_config.kaapana_dir.rglob("Chart.yaml")
            if cls._build_config.build_dir not in f.parents
        )

        logger.info("")
        logger.info(f"Found {len(chart_files)} Charts in kaapana_dir")

        for source_dir in cls._build_config.external_source_dirs:
            logger.info(f"\nSearching for Charts in: {source_dir}")
            external_charts = list(source_dir.rglob("Chart.yaml"))

            # Exclude charts that are already in the main kaapana_dir
            new_charts = {
                chart
                for chart in external_charts
                if cls._build_config.kaapana_dir not in chart.parents
            }
            chart_files |= new_charts

        # Count occurrences
        chart_counts = Counter(chart_files)
        duplicated_charts = [
            chart for chart, count in chart_counts.items() if count > 1
        ]

        if len(duplicated_charts) > 0:
            logger.warning(
                f"-> Duplicate Charts found: {len(chart_files)} vs {len(set(chart_files))}"
            )
            for chart in duplicated_charts:
                logger.warning(chart)
            logger.warning("")

        logger.info("")
        logger.info(f"--> Found {len(chart_files)} Charts across sources")
        logger.info("")
        logger.info("Generating Chart objects ...")
        logger.info("")

        charts_objects = set()
        with alive_bar(len(chart_files), dual_line=True, title="Collect-Charts") as bar:
            for chart_file in chart_files:
                bar()
                if any(
                    pat in str(chart_file)
                    for pat in (cls._build_config.build_ignore_patterns or [])
                ):
                    logger.debug(f"Ignoring chart {chart_file}")
                    continue

                chart = HelmChart.from_chartfile(
                    chart_file, build_config=cls._build_config
                )
                bar.text(chart.name)
                cls._build_state.add_chart(chart)
                charts_objects.add(chart)

        return charts_objects

    @classmethod
    def resolve_chart_dependencies(cls) -> None:
        """
        Resolve and attach chart dependencies based on unresolved declarations.

        Each chart's `unresolved_chart_dependencies` contains (name, version) tuples.
        If a matching chart exists in `charts_available` with the same version,
        it is added to the chart's `chart_dependencies`.

        If no match is found, an issue is generated.
        """
        available_charts = cls._build_state.charts_available
        available_charts_dict = {chart.name: chart for chart in available_charts}

        for chart in available_charts_dict.values():
            for dep_name, dep_version in chart.unresolved_chart_dependencies:
                candidate = available_charts_dict.get(dep_name)

                if not candidate:
                    IssueTracker.generate_issue(
                        component=cls.__name__,
                        name=chart.name,
                        msg=f"Missing dependency chart '{dep_name}:{dep_version}'",
                        level="ERROR",
                        path=chart.chartfile.parent,
                    )
                    continue

                if candidate.version != dep_version:
                    IssueTracker.generate_issue(
                        component=cls.__name__,
                        name=chart.name,
                        msg=(
                            f"Version mismatch for dependency '{dep_name}': "
                            f"expected {dep_version}, found {candidate.version}"
                        ),
                        level="ERROR",
                        path=chart.chartfile.parent,
                    )
                    continue

                chart.chart_dependencies.append(candidate)

    @staticmethod
    def expand_chart_dependencies(charts: Set[HelmChart]) -> Set[HelmChart]:
        """
        Recursively expand a set of charts to include all their dependencies.
        Returns a set of {chart_object}.
        """
        expanded_charts = set()

        def _expand(chart):
            if chart.name not in expanded_charts:
                expanded_charts.add(chart)
                for dep in chart.chart_dependencies:
                    _expand(dep)

        for chart in charts:
            _expand(chart)

        return expanded_charts

    @staticmethod
    def hash_id(path: str) -> str:
        """Generate a short SHA1 hash from a string."""
        return hashlib.sha1(path.encode("utf-8")).hexdigest()[:8]

    @staticmethod
    def _build_tree(root_charts: Set[HelmChart], include_containers=False):
        """
        Generate a Tree() from a list of root charts.
        Optionally include containers and their base images.
        Guarantees unique node IDs using a hash of the full hierarchical path.
        Only include allowed root charts and skip runtime-only charts.
        """
        ALLOWED_TYPES = {KaapanaType.PLATFORM, KaapanaType.EXTENSION_COLLECTION}

        build_tree = Tree()
        build_tree.create_node("ROOT", "ROOT")

        def add_chart(chart: HelmChart, parent_tree_id: str, path_prefix=""):
            # Skip runtime-only charts
            if getattr(chart, "runtime_only", False):
                return

            # Full path for hashing
            current_path = f"{path_prefix}/{chart.name}"
            tree_id = HelmChartService.hash_id(current_path)
            build_tree.create_node(chart.name, tree_id, parent=parent_tree_id)

            # Add containers if requested
            if include_containers and getattr(chart, "chart_containers", None):
                containers_path = f"{current_path}/containers"
                containers_id = HelmChartService.hash_id(containers_path)
                build_tree.create_node("containers", containers_id, parent=tree_id)

                for container in chart.chart_containers:
                    container_path = (
                        f"{containers_path}/{container.image_name}:{container.version}"
                    )
                    c_id = HelmChartService.hash_id(container_path)
                    build_tree.create_node(container.tag, c_id, parent=containers_id)

                    # Base images
                    if getattr(container, "base_images", None):
                        base_path = f"{container_path}/base-images"
                        base_id = HelmChartService.hash_id(base_path)
                        build_tree.create_node("base-images", base_id, parent=c_id)
                        for base in container.base_images:
                            base_img_path = (
                                f"{base_path}/{base.image_name}:{base.version}"
                            )
                            base_img_id = HelmChartService.hash_id(base_img_path)
                            build_tree.create_node(
                                f"{base.image_name}:{base.version}",
                                base_img_id,
                                parent=base_id,
                            )

            # Recurse into sub-charts / dependencies
            if getattr(chart, "chart_dependencies", None):
                subcharts_path = f"{current_path}/sub-charts"
                subcharts_id = HelmChartService.hash_id(subcharts_path)
                build_tree.create_node("sub-charts", subcharts_id, parent=tree_id)
                for dep in chart.chart_dependencies:
                    add_chart(dep, subcharts_id, path_prefix=current_path)

        # Only include allowed root charts
        for root_chart in root_charts:
            if root_chart.kaapana_type in ALLOWED_TYPES:
                add_chart(root_chart, "ROOT")

        return build_tree

    @classmethod
    def generate_build_tree(cls, root_charts: Set[HelmChart]):
        """
        Generate a build tree for all selected charts, including dependencies.
        Returns a networkx DiGraph representing chart build order.
        """
        build_tree_file = cls._build_config.build_dir / "build_tree.txt"
        build_tree = cls._build_tree(root_charts, include_containers=True)

        # Save tree to files
        build_tree.save2file(build_tree_file)
        logger.info(f"Build tree saved to: {build_tree_file}")
        for line in build_tree_file.read_text().splitlines():
            logger.info(line.strip())

    @classmethod
    def generate_platform_config(cls, platform_chart: HelmChart) -> dict:
        """
        Generate platform configuration parameters from a platform Helm chart.
        Loads deployment_config.yaml, injects metadata, and returns a dict.
        """

        logger.info(
            f"-> Generate platform deployment config for {platform_chart.name} ..."
        )

        deployment_script_config_path = (
            platform_chart.chartfile.parent / "deployment_config.yaml"
        )
        if not deployment_script_config_path.exists():
            logger.error(
                f"Could not find deployment_config.yaml for {platform_chart.name} "
                f"at {platform_chart.chartfile.parent}"
            )
            return {}

        with open(deployment_script_config_path, "r") as f:
            platform_config = yaml.load(f, Loader=yaml.FullLoader) or {}

        # Inject base metadata
        platform_config.update(
            {
                "platform_name": platform_chart.name,
                "platform_build_version": platform_chart.version,
                "container_registry_url": cls._build_config.default_registry,
            }
        )

        # Optional credentials
        if cls._build_config.include_credentials:
            platform_config.update(
                {
                    "container_registry_username": cls._build_config.registry_username,
                    "container_registry_password": cls._build_config.registry_password,
                }
            )

        # Collections
        platform_config["kaapana_collections"] = [
            {"name": chart.name, "version": platform_chart.version}
            for chart in platform_chart.kaapana_collections.values()
        ]

        # Preinstalled extensions
        platform_config["preinstall_extensions"] = [
            {"name": chart.name, "version": platform_chart.version}
            for chart in platform_chart.preinstall_extensions.values()
        ]

        return platform_config

    @classmethod
    def generate_deployment_script(
        cls,
        platform_chart: HelmChart,
        platform_params,
        kaapana_dir,
    ):
        """
        Generate deployment script from platform parameters using Jinja2 template.
        """
        if not platform_params:
            logger.error(
                f"No platform parameters found for {platform_chart.name}. Skipping script generation."
            )
            return

        file_loader = FileSystemLoader(kaapana_dir / "platforms")
        env = Environment(loader=file_loader)
        template = env.get_template("deploy_platform_template.sh")

        output = template.render(**platform_params)

        deployment_script_path = (
            Path(platform_chart.build_chart_dir).parent / "deploy_platform.sh"
        )
        deployment_script_path.parent.mkdir(parents=True, exist_ok=True)

        with open(deployment_script_path, "w") as f:
            f.write(output)

        os.chmod(deployment_script_path, 0o775)
        logger.debug(f"Deployment script generated at {deployment_script_path}")

    @classmethod
    def build_and_push_charts(cls):
        expanded_charts = cls.expand_chart_dependencies(
            cls._build_state.selected_charts
        )
        # Determine root-level charts (charts that are not dependencies of any other chart)
        dependent_chart_names = {
            dep.name for chart in expanded_charts for dep in chart.chart_dependencies
        }
        root_charts = {
            chart
            for chart in expanded_charts
            if chart.name not in dependent_chart_names
        }

        filtered_root_charts = {
            chart
            for chart in root_charts
            if chart.kaapana_type
            in {KaapanaType.EXTENSION_COLLECTION, KaapanaType.PLATFORM}
        }
        # if filtered_root_charts is Empty, try to update the chart
        cls.generate_platform_config(filtered_root_charts)

        cls.generate_build_tree(filtered_root_charts)
        exit(0)
