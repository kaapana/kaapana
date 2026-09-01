# Pure-python unit test, runs without a cluster:
#   python -m pytest tests/test_ttl_cache.py
import asyncio
import threading

import pytest

from app.ttl_cache import SingleValueTTLCache


class Fetcher:
    def __init__(self):
        self.calls = 0
        self.fail = False

    def __call__(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("k8s down")
        return f"value-{self.calls}"


def test_fresh_value_served_from_cache():
    cache = SingleValueTTLCache(ttl_seconds=1000)
    fetch = Fetcher()
    assert cache.get(fetch) == "value-1"
    assert cache.get(fetch) == "value-1"
    assert fetch.calls == 1


def test_expired_value_is_refreshed():
    cache = SingleValueTTLCache(ttl_seconds=0)
    fetch = Fetcher()
    assert cache.get(fetch) == "value-1"
    assert cache.get(fetch) == "value-2"
    assert fetch.calls == 2


def test_stale_value_served_on_refresh_failure():
    cache = SingleValueTTLCache(ttl_seconds=0)
    fetch = Fetcher()
    assert cache.get(fetch) == "value-1"
    fetch.fail = True
    assert cache.get(fetch) == "value-1"
    fetch.fail = False
    assert cache.get(fetch) == "value-3"


def test_cold_failure_propagates():
    cache = SingleValueTTLCache(ttl_seconds=10)
    fetch = Fetcher()
    fetch.fail = True
    with pytest.raises(RuntimeError):
        cache.get(fetch)
    # a later successful fetch populates the cache normally
    fetch.fail = False
    assert cache.get(fetch) == "value-2"


def test_async_fresh_value_served_from_cache():
    cache = SingleValueTTLCache(ttl_seconds=1000)
    fetch = Fetcher()
    assert asyncio.run(cache.get_async(fetch)) == "value-1"
    assert asyncio.run(cache.get_async(fetch)) == "value-1"
    assert fetch.calls == 1


def test_async_stale_value_served_on_refresh_failure():
    cache = SingleValueTTLCache(ttl_seconds=0)
    fetch = Fetcher()
    assert asyncio.run(cache.get_async(fetch)) == "value-1"
    fetch.fail = True
    assert asyncio.run(cache.get_async(fetch)) == "value-1"
    fetch.fail = False
    assert asyncio.run(cache.get_async(fetch)) == "value-3"


def test_async_get_runs_fetch_off_the_event_loop():
    cache = SingleValueTTLCache(ttl_seconds=1000)
    fetch_thread = {}

    def fetch():
        fetch_thread["id"] = threading.get_ident()
        return "value"

    async def run():
        result = await cache.get_async(fetch)
        return result, threading.get_ident()

    result, loop_thread = asyncio.run(run())
    assert result == "value"
    assert fetch_thread["id"] != loop_thread


def test_async_get_does_not_block_the_event_loop():
    cache = SingleValueTTLCache(ttl_seconds=1000)
    release = threading.Event()
    fetch_result = {}

    def slow_fetch():
        # Blocks the worker thread until the concurrently running ticker sets
        # the event -- which it can only do if the event loop was never stalled
        # by this fetch. On the buggy (in-loop) path the wait times out.
        fetch_result["released"] = release.wait(2)
        return "value"

    ticks = 0

    async def ticker():
        nonlocal ticks
        for _ in range(5):
            await asyncio.sleep(0.02)
            ticks += 1
        release.set()

    async def main():
        return await asyncio.gather(cache.get_async(slow_fetch), ticker())

    result = asyncio.run(main())
    assert result[0] == "value"
    assert ticks == 5
    assert fetch_result["released"] is True
