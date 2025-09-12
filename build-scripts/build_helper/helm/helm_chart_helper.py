import shutil
from collections import Counter
from typing import Optional

from alive_progress import alive_bar

from build_helper.build import BuildConfig, BuildState, IssueTracker
from build_helper.helm import HelmChart
from build_helper.utils import CommandUtils, get_logger

logger = get_logger()


class HelmChartHelper:
    # singleton-like class
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState) -> None:
        """Initialize the singleton with context."""
        if cls._build_config is None:
            cls._build_config = build_config
        if cls._build_state is None:
            cls._build_state = build_state

    @classmethod
    def helm_registry_login(cls, username: str, password: str) -> None:
        """Log out and log in to the Helm registry, reporting any failures as issues."""
        logger.info(f"-> Helm registry-logout: {cls._build_config.default_registry}")
        logout_cmd = ["helm", "registry", "logout", cls._build_config.default_registry]

        logout_result = CommandUtils.run(
            logout_cmd, logger=logger, timeout=10, context="helm-logout", quiet=True
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

        login_result = CommandUtils.run(
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
    def verify_helm_installed(cls) -> None:
        """Ensure Helm and Helm kubeval plugin are installed and functional."""
        if shutil.which("helm") is None:
            logger.error("Helm is not installed!")
            logger.error("-> install curl 'sudo apt install curl'")
            logger.error("-> install helm 'sudo snap install helm --classic'!")
            logger.error(
                "-> install the kubeval 'helm plugin install https://github.com/instrumenta/helm-kubeval'"
            )
            exit(1)

        helm_kubeval_cmd = ["helm", "kubeval", "--help"]
        CommandUtils.run(
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
    def collect_charts(cls) -> None:
        """
        Discover and collect all Helm charts from the main kaapana directory and external sources.

        Charts inside the build directory are ignored. Duplicate charts are detected and logged.
        Ignore patterns specified in the build configuration are applied. Each valid Chart.yaml
        file is converted into a HelmChart object and added to the build state.

        Side Effects:
            Updates cls._build_state by adding collected HelmChart objects.
            Logs progress and duplicate chart warnings.
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

        with alive_bar(len(chart_files), dual_line=True, title="Collect-Charts") as bar:
            for chart_file in chart_files:
                bar()
                if any(
                    pat in str(chart_file)
                    for pat in (cls._build_config.build_ignore_patterns or [])
                ):
                    logger.debug(f"Ignoring chart {chart_file}")
                    continue

                chart_obj = HelmChart.from_chartfile(
                    chart_file, build_config=cls._build_config
                )
                bar.text(chart_obj.name)
                cls._build_state.add_chart(chart_obj)

    @classmethod
    def resolve_chart_dependencies(cls) -> None:
        """
        Resolve and link all chart dependencies for charts in the build state.

        Iterates over each chart's unresolved dependencies (name and optional version),
        retrieves the corresponding HelmChart object via `get_chart`, and adds it to
        the chart's `chart_dependencies` set.

        Side Effects:
            Updates the `chart_dependencies` attribute of charts in `cls._build_state`.
        """

        for chart in cls._build_state.charts_available:
            for name, version in chart.unresolved_chart_dependencies:
                dep = cls.get_chart(name=name, version=version)
                if dep:
                    chart.chart_dependencies.add(dep)

    @classmethod
    def resolve_kaapana_collections(cls) -> None:
        """
        Resolve and attach Kaapana collection charts to charts in the build state.

        Checks the `deployment_config` of each chart for `kaapana_collections` entries,
        retrieves the corresponding HelmChart objects, and adds them to the chart's
        `kaapana_collections` set.

        Side Effects:
            Updates the `kaapana_collections` attribute of charts in `cls._build_state`.
        """
        for chart in cls._build_state.charts_available:
            if chart.deployment_config.get("kaapana_collections"):
                for name in chart.deployment_config["kaapana_collections"]:
                    dep = cls.get_chart(name=name)
                    if dep:
                        chart.kaapana_collections.add(dep)

    @classmethod
    def resolve_preinstall_extensions(cls) -> None:
        """
        Resolve and attach pre-install extension charts to charts in the build state.

        Checks the `deployment_config` of each chart for `preinstall_extensions` entries,
        retrieves the corresponding HelmChart objects, and adds them to the chart's
        `preinstall_extensions` set.

        Side Effects:
            Updates the `preinstall_extensions` attribute of charts in `cls._build_state`.
        """
        for chart in cls._build_state.charts_available:
            if chart.deployment_config.get("preinstall_extensions"):
                for name in chart.deployment_config["preinstall_extensions"]:
                    dep = cls.get_chart(name=name)
                    if dep:
                        chart.preinstall_extensions.add(dep)

    @classmethod
    def get_chart(
        cls,
        name: str,
        version: Optional[str] = None,
    ) -> HelmChart | None:
        """
        Retrieve a HelmChart by its name and optionally its version from the build state.

        Args:
            name: Name of the chart to retrieve.
            version: Optional specific version to match.

        Returns:
            The HelmChart object if found and version matches, otherwise None.

        Raises:
            Issues are generated via IssueTracker if the chart is not found or the version
            does not match. If exit_on_error is True or level is FATAL, the process may exit.
        """
        candidate = cls._build_state.charts_available_by_name.get(name)

        if not candidate:
            msg = f"Chart '{name}' not found in available charts."
            if cls._build_config.exit_on_error:
                IssueTracker.generate_issue(
                    component=cls.__name__, name=name, msg=msg, level="FATAL"
                )
                return None
            else:
                IssueTracker.generate_issue(
                    component=cls.__name__, name=name, msg=msg, level="ERROR"
                )
                return None

        if version and candidate.version != version:
            msg = f"Version mismatch for chart '{name}': expected {version}, found {candidate.version}"
            if cls._build_config.exit_on_error:
                IssueTracker.generate_issue(
                    component=cls.__name__, name=name, msg=msg, level="FATAL"
                )
                exit(1)
            else:
                IssueTracker.generate_issue(
                    component=cls.__name__, name=name, msg=msg, level="ERROR"
                )
                return None

        return candidate

    @classmethod
    def build_and_push_charts(cls, platform_chart: HelmChart):
        """
        Build a platform Helm chart along with its collections and dependencies, then push to registry.

        Args:
            platform_chart: The primary HelmChart representing the platform to build.

        Process:
            1. Build the main platform chart using its build directory and fake-values.yaml.
            2. Build all charts in the platform's kaapana_collections, respecting dependency order.
            3. Handle chart_dependencies for each collection, optionally making packages if not build_only.
            4. Generate final Helm packages for the platform chart.
            5. Push charts to the configured registry if build_only is False.

        Side Effects:
            Creates build artifacts on disk, updates container build directories where necessary,
            and interacts with the registry to push Helm packages.
        """
        platform_target_dir = (
            cls._build_config.build_dir / platform_chart.name / platform_chart.name
        )
        fake_values = (
            cls._build_config.kaapana_dir
            / "build-scripts/build_helper/configs/fake-values.yaml"
        )

        with alive_bar(
            bar="classic",
            # spinner="crab",
            dual_line=True,
            title=f"Generate Build-Version: {platform_chart.name}",
        ) as bar:
            platform_chart.build(
                target_dir=platform_target_dir,
                platform_build_version=platform_chart.version,
                bar=bar,
                values=fake_values,
                enable_linting=cls._build_config.enable_linting,
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
                # spinner="crab",
                dual_line=True,
                title=f"Generate Build-Version: {collection_chart.name}",
            ) as bar:
                collection_chart.build(
                    target_dir=collection_target_dir,
                    platform_build_version=platform_chart.version,
                    bar=bar,
                    values=fake_values,
                    enable_linting=cls._build_config.enable_linting,
                )
                # TODO This is currently necessary to change default build cwd for docker build command, as kaapana-extension-collection image requires charts/* being present in the directory
                if len(collection_chart.chart_containers) == 1:
                    collection_container = next(iter(collection_chart.chart_containers))
                    collection_container.container_build_dir = collection_target_dir

            with alive_bar(
                len(collection_chart.chart_dependencies),
                dual_line=True,
                title="Generate Build-Version",
            ) as bar:
                for index, chart in enumerate(collection_chart.chart_dependencies):
                    logger.info(
                        f"Collection chart {index + 1}/{len(collection_chart.chart_dependencies)}: {chart.name}:"
                    )
                    if not cls._build_config.build_only:
                        chart.make_package()

                    bar()

        platform_chart.make_package()

        if not cls._build_config.build_only:
            platform_chart.push(
                cls._build_config.default_registry,
                cls._build_config.max_push_retries,
            )
