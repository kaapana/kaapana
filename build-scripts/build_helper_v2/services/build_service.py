import json
from typing import Callable, Iterable, Set, Tuple, TypeVar

from build_helper_v2.cli.selector import interactive_select
from build_helper_v2.core.build_state import BuildState
from build_helper_v2.core.container import Container
from build_helper_v2.core.helm_chart import HelmChart
from build_helper_v2.models.build_config import BuildConfig
from build_helper_v2.services.container_service import ContainerService
from build_helper_v2.services.issue_tracker import IssueTracker
from build_helper_v2.utils.logger import get_logger
from InquirerPy import inquirer

T = TypeVar("T")  # HelmChart or Container
logger = get_logger()


class BuildService:
    _build_config: BuildConfig = None  # type: ignore
    _build_state: BuildState = None  # type: ignore

    @classmethod
    def init(cls, build_config: BuildConfig, build_state: BuildState):
        """
        Initialize the ContainerService singleton with configuration and build state.

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
    def determine_build_targets(cls) -> Tuple[Set[HelmChart], Set[Container]]:
        all_charts = cls._build_state.charts_available
        all_containers = cls._build_state.containers_available

        selected_charts_objs: Set[HelmChart] = set()
        selected_containers_objs: Set[Container] = set()

        if cls._build_config.interactive:
            # Step 1: choose Charts or Containers
            choice = inquirer.select(
                message="What do you want to select?",
                choices=["Charts", "Containers"],
            ).execute()

            # Step 2: perform fuzzy multiselect
            if choice == "Charts":
                selected_names = interactive_select(
                    [c.name for c in all_charts], "chart"
                )
                selected_charts_objs = {
                    c for c in all_charts if c.name in selected_names
                }
            elif choice == "Containers":
                selected_names = interactive_select(
                    [c.image_name for c in all_containers], "container"
                )
                selected_containers_objs = {
                    c for c in all_containers if c.image_name in selected_names
                }

        else:  # Non-interactive
            # Non-interactive: use helper
            selected_charts_objs = BuildService.filter_selection(
                cls._build_state.charts_available,
                cls._build_config.build_charts,
                get_name=lambda c: c.name,
                exit_on_error=cls._build_config.exit_on_error,
                kind="chart",
            )
            if selected_charts_objs:
                cls._build_state.selected_charts = selected_charts_objs
            else:
                selected_containers_objs = BuildService.filter_selection(
                    cls._build_state.containers_available,
                    cls._build_config.build_containers,
                    get_name=lambda c: c.image_name,
                    exit_on_error=cls._build_config.exit_on_error,
                    kind="container",
                )

                # Add all BaseImages in the queue of selected_containers
                all_base_containers = (
                    ContainerService.collect_all_local_base_containers(
                        selected_containers_objs
                    )
                )
                selected_containers_objs.update(all_base_containers)
                cls._build_state.selected_containers = selected_containers_objs

        return selected_charts_objs, selected_containers_objs

    @staticmethod
    def filter_selection(
        available: Iterable[T],
        requested: Iterable[str] | str,
        get_name: Callable[[T], str],
        exit_on_error: bool,
        kind: str,
    ) -> Set[T]:
        """
        Filters available objects based on requested names.

        - available: list of objects (HelmChart or Container)
        - requested: 'ALL' or list of names
        - get_name: function to extract name from object
        - exit_on_error: if True, raise ValueError for missing items
        - kind: "chart" or "container" (used for messages)
        """
        available_set = set(available)

        if "ALL" in requested:
            return available_set
        elif not requested:
            return set()
        else:
            selected = {obj for obj in available_set if get_name(obj) in requested}
            missing = set(requested) - {get_name(obj) for obj in selected}

            if missing:
                msg = f"The following {kind}(s) were not found: {', '.join(missing)}"
                logger.debug(msg)
                IssueTracker.generate_issue(
                    component=__name__,
                    name=f"Missing {kind}(s)",
                    msg=msg,
                    level="ERROR",
                    path="",
                )
                if exit_on_error:
                    exit(1)

            return selected

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
        image_stats = ContainerService.get_built_images_stats(
            cls.get_platform_version()
        )

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
        BuildService.report_unused_containers()
        BuildService.report_used_base_images()
        BuildService.report_available_containers()
        BuildService.report_available_charts()
        BuildService.report_unused_charts()

        if cls._build_config.enable_image_stats:
            BuildService.report_image_stats()
