from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import networkx as nx

if TYPE_CHECKING:
    from container import BaseImage, Container
    from helm_chart import HelmChart

from build_helper_v2.utils.logger import get_logger

logger = get_logger()


class BuildState:
    """
    Tracks the state of a build run and stores issues.
    Can be imported
    """

    def __init__(self, started_at: float) -> None:
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
        self.crds = set[Path]
        self.selected_charts: set[HelmChart] = set()
        self.chart_used: set[HelmChart] = set()

        self.build_graph: nx.DiGraph = None  # type: ignore

    def init(self) -> None:
        self.started_at = time.time()

    def mark_finished(self) -> None:
        self.finished_at = time.time()
        if self.started_at:
            self.duration = self.finished_at - self.started_at

    def add_container(self, container: Container) -> None:
        if container in self.containers_available:
            logger.error(
                f"Duplicated container with the same name already present: {container.image_name}. Not adding duplicated container. (Rename container if not a duplicate)"
            )
            return

        self.containers_available.add(container)

    def add_chart(self, chart: HelmChart) -> None:
        self.charts_available.add(chart)
        self.charts_available_by_name[chart.name] = chart

    def __repr__(self) -> str:
        return (
            f"<BuildState containers={len(self.containers_available)}, "
            f"charts={len(self.charts_available)}>"
        )
