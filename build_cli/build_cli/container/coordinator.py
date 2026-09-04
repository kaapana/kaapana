from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass
from queue import Empty, PriorityQueue
from threading import Lock
from typing import Iterable, Set

from build_cli.container import Container
from build_cli.container.container_helper import (
    BuildEvent,
    BuildEventType,
    ContainerHelper,
    EventQueue,
)
from build_cli.container.worker import BuildWorker
from build_cli.ui.progress import ProgressBar


@dataclass(order=True)
class QueueItem:
    """
    Item stored in the ready queue.

    Attributes:
        priority:
            Lower values indicate higher scheduling priority.
        container:
            The container ready to be processed.
    """

    priority: int
    container: Container


class BuildCoordinator:
    """
    Thread-safe coordinator for dependency-aware container builds.
    """

    def __init__(self, containers: Iterable[Container]) -> None:
        self.waiting: Set[Container] = set(containers)
        self.ready_queue: PriorityQueue[QueueItem] = PriorityQueue()
        self.event_queue: EventQueue = EventQueue()
        self.lock = Lock()
        self.abort_requested = False

    def start(self) -> None:
        """ """
        self._initialize_ready_queue()

        with ProgressBar(
            total=len(ContainerHelper._build_state.selected_containers),
            title="Building Containers",
            containers=self.waiting,
        ) as self.progress_bar:

            with ThreadPoolExecutor(
                max_workers=ContainerHelper._build_config.parallel_processes
            ) as executor:
                futures: set[Future] = set()

                # Initial scheduling
                self._schedule_ready(executor, futures)

                while (
                    futures or self._has_pending() or not self.event_queue.empty()
                ) and not self.abort_requested:
                    # 1. Handle all currently queued events. `wait()` below can
                    # reap several already-completed futures in a single call
                    # (despite return_when=FIRST_COMPLETED), while a single
                    # event_queue.get() only drains one event per iteration.
                    # If that happens on the final container(s), the loop's
                    # exit condition could become true before every event is
                    # processed, permanently dropping a progress_bar.advance()
                    # even though the container built and pushed successfully.
                    # Draining the queue fully here (plus the event_queue.empty()
                    # check above) closes that race.
                    got_event = False
                    while True:
                        try:
                            event = self.event_queue.get_nowait()
                        except Empty:
                            break
                        got_event = True
                        self._handle_event(event)
                        self.event_queue.task_done()

                    if not got_event:
                        try:
                            event = self.event_queue.get(timeout=0.1)
                            self._handle_event(event)
                            self.event_queue.task_done()
                        except Empty:
                            pass

                    # 2. Schedule newly-ready containers
                    self._schedule_ready(executor, futures)

                    # 3. Reap completed futures
                    done, pending = wait(
                        futures,
                        timeout=0,
                        return_when=FIRST_COMPLETED,
                    )
                    futures = pending

                if self.abort_requested:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return

    def _schedule_ready(
        self,
        executor: ThreadPoolExecutor,
        futures: set[Future],
    ) -> None:
        if self.abort_requested:
            ### Stop scheduling new workers
            return
        while True:
            try:
                item = self.ready_queue.get_nowait()
            except Empty:
                return

            futures.add(executor.submit(self._process_container, item.container))

    def _initialize_ready_queue(self) -> None:
        """
        Populate the ready queue with containers whose dependencies
        are already satisfied.
        """
        with self.lock:
            # Iterate over a snapshot to allow safe mutation of `waiting`
            for container in list(self.waiting):
                if container.all_dependencies_ready():
                    priority = 0 if container.local_image else 1
                    self.ready_queue.put(
                        QueueItem(priority=priority, container=container)
                    )
                    self.waiting.remove(container)

    def mark_completed(self, container: Container) -> None:
        """
        Mark a container as completed and enqueue any newly-unblocked
        dependent containers.
        """
        if self.abort_requested:
            return
        with self.lock:
            for container in list(self.waiting):
                if container.all_dependencies_ready():
                    priority = 0 if container.local_image else 1
                    self.ready_queue.put(
                        QueueItem(priority=priority, container=container)
                    )
                    self.waiting.remove(container)

    def _has_pending(self) -> bool:
        """
        Returns True if containers remain unbuilt.
        """
        with self.lock:
            return bool(self.waiting)

    def _process_container(self, container: Container) -> None:
        """
        Process a single container: build and push it.
        """
        worker = BuildWorker()
        worker.process_container(container, self.event_queue)

    def _handle_event(
        self,
        event: BuildEvent,
    ) -> None:
        """
        Handle a build event emitted by a worker.
        """
        match event.type:
            case BuildEventType.FINISHED:
                self.mark_completed(event.container)
                self.progress_bar.advance(
                    last_processed_container=event.container, advance=1
                )
                self.progress_bar.finished_print(event.container)

            case BuildEventType.SKIPPED:
                self.mark_completed(event.container)
                self.progress_bar.advance(
                    last_processed_container=event.container, advance=1
                )

            case BuildEventType.BUILT:
                if ContainerHelper._build_config.build_only:
                    self.mark_completed(event.container)
                    self.progress_bar.advance(
                        last_processed_container=event.container, advance=1
                    )

            case BuildEventType.FAILED:
                self.mark_completed(event.container)
                self.progress_bar.advance(
                    last_processed_container=event.container, advance=1
                )

                if ContainerHelper._build_config.exit_on_error:
                    self.abort_requested = True
                    e = event.error or RuntimeError(
                        f"Build failed for {event.container.tag}"
                    )
                    self.abort_exception = e
