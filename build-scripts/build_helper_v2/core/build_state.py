import time
from typing import List, Optional


class BuildState:
    """Tracks the state of a build run (containers, charts, issues)."""

    def __init__(self) -> None:
        self.started_at: float = time.time()
        self.finished_at: Optional[float] = None
        self.duration: Optional[float] = None
        self.issues: List[Issue] = []

        # Containers
        self.container_images_available: List[Container] = []
        self.base_images_used: Dict[BaseImage, List[Container]] = defaultdict(list)

        # Charts
        self.charts_available: List[HelmChart] = []

    def mark_finished(self) -> None:
        """Mark the build as finished and compute duration."""
        self.finished_at = time.time()
        self.duration = self.finished_at - self.started_at

    def add_issue(self, issue: Issue) -> None:
        self.issues.append(issue)

    def add_container(self, container: Container) -> None:
        self.container_images_available.append(container)
        for base in container.base_images:
            self.base_images_used[base].append(container)

    def add_chart(self, chart: HelmChart) -> None:
        self.charts_available.append(chart)

    def __repr__(self) -> str:
        return (
            f"<BuildState containers={len(self.container_images_available)}, "
            f"charts={len(self.charts_available)}, issues={len(self.issues)}>"
        )