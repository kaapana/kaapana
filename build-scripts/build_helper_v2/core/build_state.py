from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Optional

import networkx as nx

if TYPE_CHECKING:
    from container import BaseImage, Container
    from helm_chart import HelmChart

from build_helper_v2.utils.logger import get_logger

logger = get_logger()


class BuildState:
    """
    Tracks the state of a build run, including containers, charts,
    base images, and the build dependency graph.

    This class acts as a central state store during the build process
    and provides utilities to register containers and charts,
    as well as to track timing and overall progress.
    """

    def __init__(self, started_at: float) -> None:
        """
        Initialize a new build state.

        Args:
            started_at (float): Timestamp when the build process started.
        """
        self.started_at = started_at
        self.finished_at: Optional[float] = None
        self.duration: Optional[float] = None

        # Containers
        self.containers_available: set[Container] = set()
        self.selected_containers: set[Container] = set()
        self.base_images_used: dict[BaseImage, list[Container]] = defaultdict(list)

        # Charts
        self.charts_available: set[HelmChart] = set()
        self.charts_available_by_name: dict[str, HelmChart] = {}
        self.selected_charts: set[HelmChart] = set()
        self.chart_used: set[HelmChart] = set()

        self.build_graph: nx.DiGraph = None  # type: ignore

    def init(self) -> None:
        """
        Reset and mark the build as started.

        Updates ``started_at`` to the current timestamp.
        """
        self.started_at = time.time()

    def mark_finished(self) -> None:
        """
        Mark the build as finished and calculate duration.

        Sets ``finished_at`` to the current timestamp and
        updates ``duration`` if ``started_at`` is defined.
        """
        self.finished_at = time.time()
        if self.started_at:
            self.duration = self.finished_at - self.started_at

    def add_container(self, container: Container) -> None:
        """
        Register a container in the build state.

        Args:
            container (Container): The container object to register.

        Side Effects:
            Adds the container to ``containers_available``.
        """
        if container in self.containers_available:
            logger.error(
                f"Duplicated container with the same name already present: {container.image_name}. Not adding duplicated container. (Rename container if not a duplicate)"
            )
            return

        self.containers_available.add(container)

    def add_chart(self, chart: HelmChart) -> None:
        """
        Register a Helm chart in the build state.

        Args:
            chart (HelmChart): The Helm chart object to register.

        Side Effects:
            Adds the chart to ``charts_available`` and
            ``charts_available_by_name`` keyed by chart name.
        """
        if chart in self.charts_available:
            logger.error(
                f"Duplicated chart with the same name already present: {chart.name}. Not adding duplicated chart. (Rename chart if not a duplicate)"
            )
            return
        self.charts_available.add(chart)
        self.charts_available_by_name[chart.name] = chart

    def __repr__(self) -> str:
        return (
            f"<BuildState containers={len(self.containers_available)}, "
            f"charts={len(self.charts_available)}>"
        )
