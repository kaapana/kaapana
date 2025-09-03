import hashlib
import os
import shutil
from collections import Counter
from pathlib import Path
from typing import Set

from alive_progress import alive_bar
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container
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
    def _resolve_named_dependencies(
        cls,
        chart: HelmChart,
        unresolved: set[str | tuple[str, str]],
        attach_to: str,
        require_version: bool = False,
    ) -> None:
        """
        Resolve a set of named dependencies for a given chart.

        Parameters:
            chart: HelmChart object to attach dependencies to
            unresolved: set of names or (name, version) tuples
            attach_to: attribute name on chart to store resolved objects
                ('chart_dependencies', 'kaapana_collections', 'preinstall_extensions')
            require_version: whether to check versions (True for chart_dependencies, False otherwise)
        """
        available_charts_dict = {c.name: c for c in cls._build_state.charts_available}
        resolved: set[HelmChart] = set()

        for item in unresolved:
            if isinstance(item, str):
                name = item
                version = None
            elif isinstance(item, tuple) and len(item) == 2:
                name, version = item
            else:
                IssueTracker.generate_issue(
                    component=cls.__name__,
                    name=chart.name,
                    msg=f"Unable to resolve reference '{name}'"
                    + (f":{version}" if version else ""),
                    level="ERROR",
                    path=chart.chartfile.parent,
                )

            candidate = available_charts_dict.get(name)
            if not candidate:
                IssueTracker.generate_issue(
                    component=cls.__name__,
                    name=chart.name,
                    msg=f"Missing dependency '{name}'"
                    + (f":{version}" if version else ""),
                    level="ERROR",
                    path=chart.chartfile.parent,
                )
                continue

            if require_version and candidate.version != version:
                IssueTracker.generate_issue(
                    component=cls.__name__,
                    name=chart.name,
                    msg=f"Version mismatch for dependency '{name}': expected {version}, found {candidate.version}",
                    level="ERROR",
                    path=chart.chartfile.parent,
                )
                continue

            resolved.add(candidate)
        setattr(chart, attach_to, resolved)

    @classmethod
    def resolve_chart_dependencies(cls) -> None:
        for chart in cls._build_state.charts_available:
            cls._resolve_named_dependencies(
                chart=chart,
                unresolved=chart.unresolved_chart_dependencies,
                attach_to="chart_dependencies",
                require_version=True,
            )

    @classmethod
    def resolve_kaapana_collections(cls) -> None:
        for chart in cls._build_state.charts_available:
            cls._resolve_named_dependencies(
                chart=chart,
                unresolved=chart.unresolved_kaapana_collections,
                attach_to="kaapana_collections",
                require_version=False,
            )

    @classmethod
    def resolve_preinstall_extensions(cls) -> None:
        for chart in cls._build_state.charts_available:
            cls._resolve_named_dependencies(
                chart=chart,
                unresolved=chart.unresolved_preinstall_extensions,
                attach_to="preinstall_extensions",
                require_version=False,
            )

    @staticmethod
    def expand_chart_dependencies(charts: Set[HelmChart]) -> Set[HelmChart]:
        """
        Recursively expand a set of charts to include all their dependencies.
        Returns a set of {chart_object}.
        """
        expanded_charts = set()

        def _expand(chart):
            if chart not in expanded_charts:
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

        # Check for exactly one platform chart
        platform_charts = [
            chart
            for chart in filtered_root_charts
            if chart.kaapana_type == KaapanaType.PLATFORM
            and chart.name in cls._build_config.platform_filter
        ]

        if len(platform_charts) != 1:
            logger.error(f"No single root platform chart found: {platform_charts}")
            exit(1)

        # Assign the single platform chart
        platform_chart = platform_charts[0]

        # Separate extension charts
        root_collections = {
            chart for chart in filtered_root_charts if chart != platform_chart
        }

        # Check for missing extensions (expected but not present)
        missing_extensions = root_collections - platform_chart.kaapana_collections
        if missing_extensions:
            logger.error(
                f"Platform chart '{platform_chart.name}' is missing extensions: {list(missing_extensions)}"
            )

        # Check for unused extensions (present in platform but not in root charts)
        unused_extensions = platform_chart.kaapana_collections - root_collections
        if unused_extensions:
            logger.warning(
                f"Platform chart '{platform_chart.name}' has unused extensions: {list(unused_extensions)}"
            )

        # Exit if critical missing extensions exist
        if missing_extensions:
            exit(1)

        # Proceed with generating config and build tree
        cls.generate_deployment_script(
            platform_chart=platform_chart, kaapana_dir=cls._build_config.kaapana_dir
        )
        # Not important
        cls.generate_build_tree(
            platform_chart=platform_chart, root_charts=filtered_root_charts
        )
        cls.build_platform(platform_chart=platform_chart)
        cls._build_state.selected_containers = cls.collect_chart_containers(
            platform_chart=platform_chart
        )

    @classmethod
    def collect_chart_containers(cls, platform_chart: HelmChart) -> Set[Container]:
        """
        Collect all containers from the platform chart, including:
        - chart_dependencies
        - kaapana_collections
        - preinstall_extensions
        recursively
        """
        all_containers: Set[Container] = set()
        visited_charts: Set[HelmChart] = set()

        def _collect(chart: HelmChart):
            if chart in visited_charts:
                return
            visited_charts.add(chart)

            # add chart's own containers
            all_containers.update(chart.chart_containers)

            # recurse into dependencies
            for dep in chart.chart_dependencies:
                _collect(dep)
            for coll in chart.kaapana_collections:
                _collect(coll)
            for ext in chart.preinstall_extensions:
                _collect(ext)

        _collect(platform_chart)
        return all_containers

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
    def generate_build_tree(
        cls, platform_chart: HelmChart, root_charts: Set[HelmChart]
    ):
        """
        Generate a build tree for all selected charts, including dependencies.
        Returns a networkx DiGraph representing chart build order.
        """
        build_tree_file = (
            cls._build_config.build_dir
            / platform_chart.name
            / f"tree-{platform_chart.name}"
        )
        build_tree = cls._build_tree(root_charts, include_containers=True)

        # Save tree to files
        build_tree.save2file(build_tree_file)
        logger.info(f"Build tree saved to: {build_tree_file}")
        for line in build_tree_file.read_text().splitlines():
            logger.info(line.strip())

    @classmethod
    def generate_deployment_script(
        cls,
        platform_chart: HelmChart,
        kaapana_dir: Path,
    ):
        """
        Generate deployment script from platform parameters using Jinja2 template.
        """
        platform_config = {
            "platform_name": platform_chart.name,
            "platform_build_version": platform_chart.version,
            "container_registry_url": cls._build_config.default_registry,
            "kaapana_collections": [
                {"name": chart.name, "version": platform_chart.version}
                for chart in platform_chart.kaapana_collections
            ],
            "preinstall_extensions": [
                {"name": chart.name, "version": platform_chart.version}
                for chart in platform_chart.preinstall_extensions
            ],
        }
        if cls._build_config.include_credentials:
            platform_config.update(
                {
                    "container_registry_username": cls._build_config.registry_username,
                    "container_registry_password": cls._build_config.registry_password,
                }
            )

        file_loader = FileSystemLoader(kaapana_dir / "platforms")
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
    def build_platform(cls, platform_chart: HelmChart):
        """
        Build the platform chart and all its collections with separate progress bars.
        """
        # -------------------
        # 1. Build platform
        # -------------------
        platform_target_dir = (
            cls._build_config.build_dir / platform_chart.name / platform_chart.name
        )
        with alive_bar(
            bar="classic",
            spinner="crab",
            dual_line=True,
            title=f"Generate Build-Version: {platform_chart.name}",
        ) as bar:
            platform_chart.build(
                target_dir=platform_target_dir,
                platform_build_version=platform_chart.version,
                bar=bar,
            )

        # -------------------
        # 2. Build collections
        # -------------------
        for collection_chart in platform_chart.kaapana_collections:
            collection_target_dir = (
                cls._build_config.build_dir
                / platform_chart.name
                / collection_chart.name
            )
            with alive_bar(
                bar="classic",
                spinner="dots",
                dual_line=True,
                title=f"Generate Build-Version: {collection_chart.name}",
            ) as bar:
                collection_chart.build(
                    target_dir=collection_target_dir,
                    platform_build_version=platform_chart.version,
                    bar=bar,
                )

            with alive_bar(
                len(collection_chart.chart_dependencies),
                dual_line=True,
                title="Generate Build-Version",
            ) as bar:
                for index, chart in enumerate(collection_chart.chart_dependencies):
                    logger.info(
                        f"Collection chart {index + 1}/{len(collection_chart.chart_dependencies)}: {chart.name}:"
                    )

                    if cls._build_config.enable_linting:
                        chart.lint_chart()
                        chart.lint_kubeval()

                    if not cls._build_config.build_only:
                        chart.make_package()

                    bar()

            if cls._build_config.enable_linting:
                collection_chart.lint_chart()
                collection_chart.lint_kubeval()

        # -------------------
        # 3. Final linting on platform
        # -------------------
        if cls._build_config.enable_linting:
            platform_chart.lint_chart()
            platform_chart.lint_kubeval()

        platform_chart.make_package()

        if not cls._build_config.build_only:
            platform_chart.push(
                cls._build_config.default_registry,
                cls._build_config.max_push_retries,
            )
