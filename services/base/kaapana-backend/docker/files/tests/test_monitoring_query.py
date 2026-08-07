"""
Regression test for the /monitoring/query and /monitoring/query-range passthroughs.

The SanitizeQueryParams middleware HTML-escapes every query parameter, so a
client asking for `a{b="c"}` reaches the handler as `a{b=&quot;c&quot;}` --
every PromQL query with a quoted label value arrives corrupted. The handler
therefore calls `html.unescape(q)` before forwarding, and this test pins that:
what reaches the Prometheus client must be the raw query the client sent.
Dropping the unescape is silently broken, not loudly.

Same run asserts the second half of the fix: an empty Prometheus result must
raise 404 (develop's `raise HTTPException(...)` had no import at all, so that
path was a guaranteed 500, and a 204 must not carry a body).

/query-range is the sparkline backfill home-ui calls once per utilization
metric. It shares both properties -- the same unescape and the same 404 -- and
additionally forwards the window: `minutes` and `step` must reach
`MonitoringService.query_range` positionally in that order, or the chart
silently renders the wrong span. Its consumer swallows failures (returns null,
sparklines start empty), so nothing else would surface a regression here.

No live services: fastapi/app.dependencies are stubbed like in
test_admin_routers.py. The stubbed router's `get()` is made an identity
decorator so the handler stays a plain callable function, and HTTPException a
real exception class -- a MagicMock instance cannot be raised.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

FILES_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(FILES_DIR))

# Stub heavy dependencies not installed in the test environment
for mod in ("app.dependencies", "fastapi", "fastapi.responses"):
    sys.modules.setdefault(mod, MagicMock())


class HTTPExceptionStub(Exception):
    def __init__(self, status_code, detail=None):
        super().__init__(detail)
        self.status_code = status_code


fastapi_stub = sys.modules["fastapi"]
fastapi_stub.APIRouter.return_value.get.return_value = lambda fn: fn
fastapi_stub.HTTPException = HTTPExceptionStub

import app.monitoring.routers as routers  # noqa: E402


def test_custom_query_passes_unescaped_promql_and_404s_on_empty_result():
    client = MagicMock()
    client.query.return_value = {"metric": "custom-query", "value": 1.0}

    routers.custom_query("a{b=&quot;c&quot;}", client=client)

    # The middleware's escaping is undone: PromQL, not HTML, reaches Prometheus.
    client.query.assert_called_once_with("custom-query", 'a{b="c"}')

    client.query.return_value = None
    with pytest.raises(HTTPExceptionStub) as excinfo:
        routers.custom_query("up", client=client)
    assert excinfo.value.status_code == 404


def test_custom_query_range_forwards_the_window_and_404s_on_empty_result():
    client = MagicMock()
    client.query_range.return_value = [{"metric": "custom-query-range", "value": 1.0}]

    routers.custom_query_range("a{b=&quot;c&quot;}", minutes=30, step=15, client=client)

    client.query_range.assert_called_once_with("custom-query-range", 'a{b="c"}', 30, 15)

    # Defaults are the hour-at-minute-resolution window home-ui's charts assume.
    client.query_range.reset_mock()
    routers.custom_query_range("up", client=client)
    client.query_range.assert_called_once_with("custom-query-range", "up", 60, 60)

    client.query_range.return_value = []
    with pytest.raises(HTTPExceptionStub) as excinfo:
        routers.custom_query_range("up", client=client)
    assert excinfo.value.status_code == 404
