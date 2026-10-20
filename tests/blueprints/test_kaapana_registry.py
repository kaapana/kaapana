"""Pull-policy fallback for an unreachable registry (kaapana#2149).

Loads kaapana_registry.py from its file so the test needs neither Airflow nor the Flask
plugin machinery that kaapana.blueprints imports.
"""

import importlib
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

HELPER = (
    Path(__file__).resolve().parents[2]
    / "data-processing/kaapana-plugin/extension/docker/files/plugin"
    / "kaapana/blueprints/kaapana_registry.py"
)


@pytest.fixture
def real_requests(monkeypatch):
    # tests/operators/utils.py replaces sys.modules["requests"] with a MagicMock when
    # its modules are collected; the helper under test needs the real package.
    for name in [m for m in sys.modules if m.split(".")[0] == "requests"]:
        monkeypatch.delitem(sys.modules, name)
    return importlib.import_module("requests")


@pytest.fixture
def registry(real_requests):
    spec = importlib.util.spec_from_file_location("kaapana_registry", HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.requests is real_requests
    return module


@pytest.fixture
def probe(registry, monkeypatch):
    """Replaces requests.get; `probe.calls` lists probed URLs, `probe.result` is what
    the probe returns (a status code) or raises (an exception instance)."""
    state = SimpleNamespace(calls=[], result=200)

    def fake_get(url, timeout, verify):
        state.calls.append(url)
        assert verify is False
        if isinstance(state.result, Exception):
            raise state.result
        return SimpleNamespace(status_code=state.result)

    monkeypatch.setattr(registry.requests, "get", fake_get)
    return state


@pytest.mark.parametrize(
    "ref,host",
    [
        ("registry.example.com/ns/image:1.0", "registry.example.com"),
        ("registry.example.com:5000/ns/image", "registry.example.com:5000"),
        ("https://registry.example.com/ns", "registry.example.com"),
        ("registry.example.com", "registry.example.com"),
        ("localhost:32000/ns/image", "localhost:32000"),
        ("localhost:32000", "localhost:32000"),
        # Docker Hub references carry no registry host to probe.
        ("python:3.11", ""),
        ("ubuntu", ""),
        ("library/ubuntu:22.04", ""),
        ("", ""),
        (None, ""),
    ],
)
def test_registry_host(registry, ref, host):
    assert registry.registry_host(ref) == host


def test_non_always_policy_is_passed_through_without_probe(registry, probe):
    assert registry.effective_pull_policy("IfNotPresent", "reg/img") == "IfNotPresent"
    assert probe.calls == []


@pytest.mark.parametrize("status", [200, 401, 403, 404])
def test_answering_registry_keeps_always(registry, probe, status):
    probe.result = status
    policy = registry.effective_pull_policy("Always", "reg.example.com/ns/img")
    assert policy == "Always"
    assert probe.calls == ["https://reg.example.com/v2/"]


@pytest.mark.parametrize(
    "failure",
    ["ConnectTimeout", "ConnectionError", "ProxyError", "ReadTimeout", 503],
)
def test_unreachable_registry_falls_back_to_local_image(
    registry, real_requests, probe, failure
):
    probe.result = (
        getattr(real_requests.exceptions, failure)()
        if isinstance(failure, str)
        else failure
    )
    assert (
        registry.effective_pull_policy("Always", "reg.example.com/ns/img")
        == "IfNotPresent"
    )


def test_tls_error_means_the_registry_answers(registry, real_requests, probe):
    # A plain-HTTP registry (kaapanactl PLAIN_HTTP) answers the probe with something
    # that is not TLS; the peer is up, so dev mode keeps re-pulling.
    probe.result = real_requests.exceptions.SSLError()
    assert registry.effective_pull_policy("Always", "reg.example.com/ns/img") == "Always"


def test_docker_hub_image_is_not_probed(registry, probe):
    # No registry host in the reference: nothing to probe, the configured policy stays.
    assert registry.effective_pull_policy("Always", "python:3.11") == "Always"
    assert probe.calls == []


def test_custom_registry_is_probed_by_image_host(registry, real_requests, probe):
    # An operator image from a project's own registry is judged by that registry.
    probe.result = real_requests.ConnectionError()
    assert registry.effective_pull_policy("Always", "custom.example.org/x") == (
        "IfNotPresent"
    )
    assert probe.calls == ["https://custom.example.org/v2/"]


def test_probe_result_is_cached_per_host(registry, real_requests, probe):
    probe.result = real_requests.ConnectionError()
    registry.effective_pull_policy("Always", "reg.example.com/a")
    registry.effective_pull_policy("Always", "reg.example.com/b")
    registry.effective_pull_policy("Always", "other.example.com/c")
    assert probe.calls == [
        "https://reg.example.com/v2/",
        "https://other.example.com/v2/",
    ]


def test_cache_expires(registry, probe, monkeypatch):
    now = [1000.0]
    monkeypatch.setattr(registry.time, "monotonic", lambda: now[0])
    registry.effective_pull_policy("Always", "reg.example.com/a")
    now[0] += registry.CACHE_SECONDS + 1
    registry.effective_pull_policy("Always", "reg.example.com/a")
    assert len(probe.calls) == 2


def test_empty_registry_reference_keeps_configured_policy(registry, probe):
    assert registry.effective_pull_policy("Always", "") == "Always"
    assert probe.calls == []
