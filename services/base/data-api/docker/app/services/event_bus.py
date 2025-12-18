from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Dict

from fastapi import WebSocket

from app.models.events import EventMessage


logger = logging.getLogger(__name__)

_QUEUE_MAXSIZE = 512
_BATCH_MAX_EVENTS = 25
_BATCH_FLUSH_INTERVAL = 0.01  # seconds


class _ConnectionState:
    def __init__(self, websocket: WebSocket) -> None:
        self.websocket = websocket
        self.queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(
            maxsize=_QUEUE_MAXSIZE
        )
        self.sender_task: asyncio.Task[None] | None = None


class EventBus:
    """In-memory broadcast channel for lightweight frontend updates."""

    def __init__(self) -> None:
        self._connections: dict[WebSocket, _ConnectionState] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        state = _ConnectionState(websocket)
        state.sender_task = asyncio.create_task(self._connection_worker(state))
        async with self._lock:
            self._connections[websocket] = state

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            state = self._connections.pop(websocket, None)

        if state is None:
            return

        task = state.sender_task
        if task and asyncio.current_task() is not task:
            task.cancel()
            try:
                await task
            except (
                asyncio.CancelledError
            ):  # pragma: no cover - task already shutting down
                pass

        try:
            await websocket.close()
        except Exception:  # pragma: no cover - best effort
            logger.debug("Websocket already closed", exc_info=True)

    async def broadcast(self, event: EventMessage | Dict[str, Any]) -> None:
        payload = (
            event.model_dump(mode="json")
            if isinstance(event, EventMessage)
            else dict(event)
        )
        async with self._lock:
            states = list(self._connections.values())

        for state in states:
            try:
                state.queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Dropping slow websocket subscriber (queue full)")
                asyncio.create_task(self.disconnect(state.websocket))

    async def _connection_worker(self, state: _ConnectionState) -> None:
        websocket = state.websocket
        try:
            while True:
                first_event = await state.queue.get()
                batch = await self._gather_batch(state.queue, first_event)
                message = self._encode_batch(batch)
                await websocket.send_text(message)
        except asyncio.CancelledError:  # pragma: no cover - cooperative shutdown
            raise
        except Exception:
            logger.warning("Websocket send failed; disconnecting client", exc_info=True)
        finally:
            await self.disconnect(websocket)

    async def _gather_batch(
        self,
        queue: asyncio.Queue[dict[str, Any]],
        first_event: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if _BATCH_MAX_EVENTS <= 1:
            return [first_event]

        batch = [first_event]
        loop = asyncio.get_running_loop()
        deadline = loop.time() + _BATCH_FLUSH_INTERVAL

        while len(batch) < _BATCH_MAX_EVENTS:
            timeout = deadline - loop.time()
            if timeout <= 0:
                break
            try:
                next_event = await asyncio.wait_for(queue.get(), timeout=timeout)
            except asyncio.TimeoutError:
                break
            else:
                batch.append(next_event)

        return batch

    @staticmethod
    def _encode_batch(batch: list[dict[str, Any]]) -> str:
        if len(batch) == 1:
            payload: dict[str, Any] | dict[str, Any | list[dict[str, Any]]] = batch[0]
        else:
            payload = {"batch": batch}
        return json.dumps(payload)


_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
