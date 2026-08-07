"""Tiny process-wide TTL cache, kept free of kubernetes/kaapana imports so it
can be unit-tested without a live cluster."""

import asyncio
import logging
import threading
import time
from typing import Callable, Generic, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class SingleValueTTLCache(Generic[T]):
    """Caches one expensive value for a short TTL (single-worker deployment).

    While the value is fresh it is served from memory; afterwards the next
    caller refreshes it. If the refresh fails but a previous value exists, the
    stale value is served instead of erroring (same trade-off as portal-api's
    menu cache). The lock serializes refreshes in :meth:`get`, so concurrent
    callers trigger at most one fetch; :meth:`get_async` instead releases the
    lock across the (offloaded) fetch, so concurrent async callers may each
    refresh.
    """

    def __init__(self, ttl_seconds: float):
        self._ttl_seconds = ttl_seconds
        self._lock = threading.Lock()
        self._value: Optional[T] = None
        self._fetched_at: Optional[float] = None

    def get(self, fetch: Callable[[], T]) -> T:
        with self._lock:
            if (
                self._fetched_at is not None
                and time.monotonic() - self._fetched_at < self._ttl_seconds
            ):
                return self._value
            try:
                value = fetch()
            except Exception:
                if self._fetched_at is not None:
                    logger.warning(
                        "cache refresh failed, serving stale value", exc_info=True
                    )
                    return self._value
                raise
            self._value = value
            self._fetched_at = time.monotonic()
            return value

    async def get_async(self, fetch: Callable[[], T]) -> T:
        """Async variant of :meth:`get` for callers on an event loop.

        ``fetch`` is a blocking callable (e.g. a synchronous kubernetes list),
        so it runs off the event loop via :func:`asyncio.to_thread` and the
        lock is only ever held to read freshness or to store the result --
        never across the fetch -- keeping the event loop responsive while a
        refresh is in flight.
        """
        with self._lock:
            if (
                self._fetched_at is not None
                and time.monotonic() - self._fetched_at < self._ttl_seconds
            ):
                return self._value
        try:
            value = await asyncio.to_thread(fetch)
        except Exception:
            with self._lock:
                if self._fetched_at is not None:
                    logger.warning(
                        "cache refresh failed, serving stale value", exc_info=True
                    )
                    return self._value
                raise
        with self._lock:
            self._value = value
            self._fetched_at = time.monotonic()
            return value
