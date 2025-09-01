from dataclasses import dataclass
from threading import Lock
from typing import Dict

from rich.console import Console
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.table import Table


@dataclass
class Result:
    tag: str
    status: str
    build_time: str
    push_time: str


class ProgressBar:
    def __init__(self, total: int, title: str, results: Dict[str, Result], use_rich: bool = False):
        """
        Unified progress bar:
        - use_rich=False => no Rich dashboard (you could plug in alive_bar separately)
        - use_rich=True  => Rich dashboard + overall progress bar
        """
        self.total = total
        self.title = title
        self.results = results
        self.use_rich = use_rich
        self._lock = Lock()

        self._console = None
        self._dashboard_live = None
        self._rich_progress = None
        self._task_id = None

    def __enter__(self):
        if self.use_rich:
            self._console = Console()
            self._dashboard_live = Live(self._render_dashboard(), console=self._console, refresh_per_second=2)
            self._dashboard_live.__enter__()

            self._rich_progress = Progress(
                TextColumn("{task.description}"),
                BarColumn(),
                "[progress.percentage]{task.percentage:>3.0f}%",
                TimeElapsedColumn(),
                console=self._console,
                transient=False,
            )
            self._task_id = self._rich_progress.add_task(self.title, total=self.total)
            self._rich_progress.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.use_rich:
            if self._rich_progress:
                self._rich_progress.stop()
            if self._dashboard_live:
                self._dashboard_live.__exit__(exc_type, exc_val, exc_tb)

    def advance(self):
        """Advance overall progress by one step."""
        with self._lock:
            if self.use_rich and self._rich_progress and self._task_id is not None:
                self._rich_progress.update(self._task_id, advance=1)

    def refresh(self):
        """Refresh the dashboard table."""
        if self.use_rich and self._dashboard_live:
            with self._lock:
                self._dashboard_live.update(self._render_dashboard())

    def _render_dashboard(self):
        """Render results table below the progress bar."""
        table = Table(show_header=True, header_style="bold")
        table.add_column("Container", style="dim", overflow="fold")
        table.add_column("Status")
        table.add_column("Build Time")
        table.add_column("Push Time")

        for r in self.results.values():
            table.add_row(r.tag, str(r.status), r.build_time, r.push_time)

        return table
