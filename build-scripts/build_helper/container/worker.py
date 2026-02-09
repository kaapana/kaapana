from build_helper.container.container import Container, Status
from build_helper.container.container_helper import (
    BuildEvent,
    BuildEventType,
    EventQueue,
    ContainerHelper,
)


class BuildWorker:

    def process_container(self, container: Container, event_queue: EventQueue) -> None:
        """
        Process a single container.
        """

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
        else:
            self._emit_event(
                BuildEvent(type=BuildEventType.BUILT, container=container),
                event_queue,
            )

        if container.status in {Status.SKIPPED, Status.BUILT_ONLY}:
            self._emit_event(
                BuildEvent(type=BuildEventType.SKIPPED, container=container),
                event_queue,
            )
            return

        if ContainerHelper._build_config.build_only:
            self._emit_event(
                BuildEvent(type=BuildEventType.BUILT, container=container),
                event_queue,
            )
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
