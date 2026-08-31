from build_cli.container.container import Container, Status
from build_cli.container.container_helper import (
    BuildEvent,
    BuildEventType,
    ContainerHelper,
    EventQueue,
)


class BuildWorker:

    def process_container(self, container: Container, event_queue: EventQueue) -> None:
        """
        Process a single container. Guaranteed to emit a terminal event.

        Anything escaping the build/push steps - including the SystemExit that
        IssueTracker.generate_issue raises under exit_on_error, which would
        otherwise die silently inside the ThreadPoolExecutor thread - is turned
        into a FAILED event. Without a terminal event the coordinator would wait
        on the container's dependents forever and could never abort.
        """
        try:
            self._process_container(container, event_queue)
        except BaseException as e:  # noqa: B036 - SystemExit must be caught here
            container.status = Status.FAILED
            self._emit_event(
                BuildEvent(type=BuildEventType.FAILED, container=container, error=e),
                event_queue,
            )

    def _process_container(self, container: Container, event_queue: EventQueue) -> None:
        self._emit_event(
            BuildEvent(type=BuildEventType.STARTED, container=container),
            event_queue,
        )

        build_issue = container.build(ContainerHelper._build_config)

        # Determine outcome after build
        if build_issue:
            container.status = Status.FAILED
            self._emit_event(
                BuildEvent(
                    type=BuildEventType.FAILED, container=container, issue=build_issue
                ),
                event_queue,
            )
            return

        if container.status in {Status.SKIPPED, Status.BUILT_ONLY}:
            self._emit_event(
                BuildEvent(type=BuildEventType.SKIPPED, container=container),
                event_queue,
            )
            return

        self._emit_event(
            BuildEvent(type=BuildEventType.BUILT, container=container),
            event_queue,
        )

        if ContainerHelper._build_config.build_only:
            return

        # Push phase
        push_issue = container.push(ContainerHelper._build_config)
        if push_issue:
            self._emit_event(
                BuildEvent(
                    type=BuildEventType.FAILED, container=container, issue=push_issue
                ),
                event_queue,
            )
            return

        self._emit_event(
            BuildEvent(type=BuildEventType.FINISHED, container=container),
            event_queue,
        )

    def _emit_event(self, event: BuildEvent, event_queue: EventQueue) -> None:
        """
        Emit a build event.
        """
        event_queue.put(event)