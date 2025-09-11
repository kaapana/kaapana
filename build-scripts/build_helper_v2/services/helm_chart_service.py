import shutil
from collections import Counter
from typing import Optional, Set

from alive_progress import alive_bar
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.helm_chart import HelmChart
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.command_helper import CommandHelper
from build_helper_v2.utils.logger import get_logger

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
        for chart in cls._build_state.charts_available:
            for name, version in chart.unresolved_chart_dependencies:
                dep = cls.get_chart(name=name, version=version)
                if dep:
                    chart.chart_dependencies.add(dep)

    @classmethod
    def resolve_kaapana_collections(cls) -> None:
        for chart in cls._build_state.charts_available:
            if chart.deployment_config.get("kaapana_collections"):
                for name in chart.deployment_config["kaapana_collections"]:
                    dep = cls.get_chart(name=name)
                    if dep:
                        chart.kaapana_collections.add(dep)

    @classmethod
    def resolve_preinstall_extensions(cls) -> None:
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
        Build the platform chart along with all its dependencies and collections.
        """
        platform_target_dir = (
            cls._build_config.build_dir / platform_chart.name / platform_chart.name
        )
        fake_values = (
            cls._build_config.kaapana_dir
            / "build-scripts/build_helper_v2/fake-values.yaml"
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
