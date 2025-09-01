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
    @staticmethod
    def determine_build_targets(
        build_config: BuildConfig, build_state: BuildState
    ) -> Tuple[Set[HelmChart], Set[Container]]:
        all_charts = build_state.charts_available
        all_containers = build_state.container_images_available

        selected_charts_objs: Set[HelmChart] = set()
        selected_containers_objs: Set[Container] = set()

        if build_config.interactive:
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
                build_state.charts_available,
                build_config.build_charts,
                get_name=lambda c: c.name,
                exit_on_error=build_config.exit_on_error,
                kind="chart",
            )

            selected_containers_objs = BuildService.filter_selection(
                build_state.container_images_available,
                build_config.build_containers,
                get_name=lambda c: c.image_name,
                exit_on_error=build_config.exit_on_error,
                kind="container",
            )

            # Add all BaseImages in the queue of selected_containers
            all_base_containers = ContainerService.collect_all_local_base_containers(selected_containers_objs)
            selected_containers_objs.update(all_base_containers)

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
