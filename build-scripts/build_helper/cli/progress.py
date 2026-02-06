import logging
from queue import SimpleQueue
from threading import Lock
from typing import Set

from alive_progress import alive_bar
from rich.console import Console, Group
from rich.live import Live
from rich.progress import BarColumn, Progress, TextColumn
from rich.style import Style
from rich.table import Table

from build_helper.container import Container, Status
from build_helper.utils import get_logger

logger = get_logger()


class ProgressBar:
    """
    Unified progress bar implementation supporting both `alive-progress` and `rich`.

    When `use_rich=False`, it uses `alive-progress` (lightweight console progress).
    When `use_rich=True`, it renders a live Rich dashboard with:
        - An overall progress bar
        - A detailed table of container statuses

    Attributes:
        total (int): Total number of steps (e.g., containers to process).
        title (str): Title of the progress bar.
        containers (Set[Container]): Set of containers being tracked.
        use_rich (bool): Whether to use Rich dashboard or alive-progress.
        _lock (Lock): Thread lock to protect updates.
        _finished_queue (SimpleQueue): Queue for finished container events.
        status_colors (dict): Mapping from `Status` to Rich color names.
        status_order (List[Status]): Ordering of statuses in the dashboard.
        finished_states (Set[Status]): States considered "finished".
    """

    def __init__(
        self,
        total: int,
        title: str,
        containers: Set[Container],
    ):
        """
        Initialize the progress bar.

        Args:
            total (int): Total number of items to process.
            title (str): Title of the progress bar.
            containers (Set[Container]): Set of containers being tracked.
        """
        self.total = total
        self.title = title
        self.containers = containers
        self._lock = Lock()
        self._finished_queue: SimpleQueue = SimpleQueue()

        # Rich backend
        self._console = None
        self.logfile_console = None
        self._dashboard_live = None
        self._rich_progress = None
        self._task_id = None

        # Alive backend
        self._alive_cm = None
        self._alive_bar = None

        self.container_width = max(
            [len(c.tag) for c in self.containers] + [len("Container")]
        )
        self.status_width = max([len(str(s)) for s in Status] + [len("Status")])
        self.build_time_width = len("Build Time")
        self.push_time_width = len("Push Time")

        # Status to color mapping
        self.status_colors = {
            Status.BUILDING: "blue",
            Status.BUILT: "blue",
            Status.PUSHING: "blue",
            Status.PUSHED: "green",
            Status.BUILT_ONLY: "green",
            Status.NOTHING_CHANGED: "green",
            Status.SKIPPED: "yellow",
            Status.FAILED: "red",
        }

        # Define custom status ordering
        self.status_order = [
            Status.BUILDING,
            Status.BUILT,
            Status.PUSHING,
            Status.PUSHED,
            Status.BUILT_ONLY,
            Status.NOTHING_CHANGED,
            Status.SKIPPED,
            Status.FAILED,
        ]
        self.finished_states = {
            Status.BUILT,
            Status.PUSHED,
            Status.BUILT_ONLY,
            Status.NOTHING_CHANGED,
            Status.SKIPPED,
            Status.FAILED,
        }

    def __enter__(self):
        """
        Enter context manager, initializing either Rich or alive-progress backend.

        Returns:
            ProgressBar: Self instance, ready for updates.
        """

        # === alive_bar setup ===
        self._alive_cm = alive_bar(self.total, title=self.title)
        self._alive_bar = self._alive_cm.__enter__()

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager, closing progress bar backends.

        Args:
            exc_type (Exception): Exception type (if raised).
            exc_val (Exception): Exception value.
            exc_tb (traceback): Traceback object.
        """

        if self._alive_cm:
            self._alive_cm.__exit__(exc_type, exc_val, exc_tb)

    def advance(self, last_processed_container: Container, advance: int):
        """
        Advance progress by a given step.

        Args:
            last_processed_container (Container): The most recently processed container.
            advance (int): Number of steps to advance.
        """
        with self._lock:
            if self._alive_bar:
                for _ in range(advance):
                    self._alive_bar()  # increments
                # Update the text shown next to alive_bar
                self._alive_bar.text(
                    f"{last_processed_container.tag:<{self.container_width}} -> {last_processed_container.status}"
                )

    def refresh(self, clear=False):
        """
        Refresh the Rich dashboard table.

        Args:
            clear (bool, optional): Whether to clear the console first. Defaults to False.
        """
        if clear and self._console:
            self._console.clear()

    def finished_print(self, last_processed_container: Container):
        """
        Print a finished container status line to the console and log file.

        Args:
            title (str): Prefix title for the log line.
            last_processed_container (Container): The container that has just finished.
        """
        with self._lock:
            tag = f"{last_processed_container.tag:<{self.container_width}}"
            build_time = (
                f"{last_processed_container.build_time:0.2f}s"
                if last_processed_container.build_time != "-"
                else "-"
            )
            push_time = (
                f"{last_processed_container.push_time:0.2f}s"
                if last_processed_container.push_time != "-"
                else "-"
            )
            status = f"{str(last_processed_container.status):<{self.status_width}}"

            logger.info(f"{tag} - build: {build_time} - push: {push_time}")
