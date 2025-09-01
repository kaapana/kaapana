from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING, Dict, List, Optional, Set

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
        self.container_images_available: Set[Container] = set()
        self.build_containers: Set[Container] = set()
        self.base_images_used: Dict[BaseImage, List[Container]] = defaultdict(list)

        # Charts
        self.charts_available: Set[HelmChart] = set()
        self.chart_used: Set[HelmChart] = set()

    def init(self) -> None:
        self.started_at = time.time()

    def mark_finished(self) -> None:
        self.finished_at = time.time()
        if self.started_at:
            self.duration = self.finished_at - self.started_at

    def add_container(self, container: Container) -> None:
        if container in self.container_images_available:
            logger.error(f"Duplicated container with the same name already present: {container.image_name}. Not adding duplicated container. (Rename container if not a duplicate)")
            return
            
        self.container_images_available.add(container)
        for base in container.base_images:
            self.base_images_used[base].append(
                container
            )  # TODO see if this is necesarry here as all the containers have their base_image information available, we maybe don't need to collect it immediately, only after the selection of charts and containers.

    def add_chart(self, chart: HelmChart) -> None:
        self.charts_available.add(chart)

    def __repr__(self) -> str:
        return (
            f"<BuildState containers={len(self.container_images_available)}, "
            f"charts={len(self.charts_available)}>"
        )
