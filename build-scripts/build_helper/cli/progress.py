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
        use_rich: bool = False,
    ):
        """
        Initialize the progress bar.

        Args:
            total (int): Total number of items to process.
            title (str): Title of the progress bar.
            containers (Set[Container]): Set of containers being tracked.
            use_rich (bool, optional): If True, use Rich dashboard. Defaults to False.
        """
        self.total = total
        self.title = title
        self.containers = containers
        self.use_rich = use_rich
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
        if self.use_rich:
            self._console = Console()
            log_file = None
            for handler in logger.handlers:
                if isinstance(handler, logging.FileHandler):
                    log_file = handler.baseFilename
                    break

            if log_file:
                self.logfile_console = Console(
                    file=open(log_file, "a"), record=False, force_terminal=False
                )

            # create the progress bar first
            self._rich_progress = Progress(
                TextColumn("[white]{task.description}"),
                BarColumn(
                    bar_width=None,
                    complete_style=Style(color="white"),
                    finished_style=Style(color="white"),
                ),
                TextColumn("[white]{task.completed}/{task.total}[/white]"),
                TextColumn("[white]{task.percentage:>3.0f}%][/white]"),
                TextColumn("[white]{task.elapsed:.2f}s[/white]", justify="right"),
                console=self._console,
                transient=False,
            )
            self._task_id = self._rich_progress.add_task(self.title, total=self.total)
            self._rich_progress.start()

            # render both progress bar and dashboard table in a Group
            self._dashboard_live = Live(
                Group(self._rich_progress, self._render_dashboard()),
                console=self._console,
                refresh_per_second=2,
            )
            self._dashboard_live.__enter__()
        else:
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
        if self.use_rich and self._rich_progress and self._dashboard_live:
            self._rich_progress.stop()
            self._dashboard_live.__exit__(exc_type, exc_val, exc_tb)

        else:
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
            if self.use_rich and self._rich_progress and self._task_id is not None:
                status = last_processed_container.status
                self._rich_progress.update(
                    self._task_id,
                    description=f"{self.title} | {last_processed_container.tag: <{self.container_width}} -> {status: <{self.status_width}}",
                    advance=advance,
                )
            elif self._alive_bar:
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
        if self.use_rich and self._dashboard_live:
            with self._lock:
                self._dashboard_live.update(self._render_dashboard())

    def _render_dashboard(self):
        """
        Render the dashboard table of containers and their statuses.

        Returns:
            Table: Rich table object containing container status rows.
        """
        table = Table(show_header=True, header_style="bold")
        # Precompute max widths

        table.add_column(
            "Container", style="dim", overflow="fold", width=self.container_width
        )
        table.add_column("Status", width=self.status_width)
        table.add_column("Build Time", width=self.build_time_width)
        table.add_column("Push Time", width=self.push_time_width)

        order_index = {status: i for i, status in enumerate(self.status_order)}

        filtered_results = [
            c for c in self.containers if c.status not in self.finished_states
        ]

        # Sort results by status order first, then alphabetically by container tag
        sorted_results = sorted(
            filtered_results,
            key=lambda c: (order_index.get(c.status, 99), c.tag.lower()),
        )

        # Add rows with color
        for c in sorted_results:
            color = self.status_colors.get(c.status)
            table.add_row(
                c.tag,
                f"[{color}]{str(c.status)}[/{color}]" if color else str(c.status),
                (
                    f"{c.build_time:0.2f}s"
                    if c.build_time != "-"
                    else "-" f"{c.push_time:0.2f}s" if c.push_time != "-" else "-"
                ),
            )

        return table

    def finished_print(self, title: str, last_processed_container: Container):
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

            if self.use_rich:
                color = self.status_colors.get(last_processed_container.status, "white")
                if self._console:
                    self._console.print(
                        f"{title}: {tag} -> [{color}]{status}[/{color}] | "
                        f"Build: {build_time} | Push: {push_time}",
                        markup=True,
                        highlight=False,
                    )
                if self.logfile_console:
                    self.logfile_console.print(
                        f"{title}: {tag} -> [{color}]{status}[/{color}] | "
                        f"Build: {build_time} | Push: {push_time}",
                        markup=True,
                        highlight=False,
                    )
            else:
                logger.info(f"{tag} - build: {build_time} - push: {push_time}")
