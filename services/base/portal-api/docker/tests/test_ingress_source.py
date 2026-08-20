"""The kubernetes package is deliberately absent from tests/requirements.txt --
that absence is what proves ingress_source' imports stay lazy. So the client is
faked through sys.modules here instead of installed.
"""

import asyncio
import sys
from types import ModuleType, SimpleNamespace

import app.ingress_source as ingress_source
import pytest


def rule(paths: list[str] | None) -> SimpleNamespace:
    """An ingress rule; paths=None models a rule without an http section."""
    if paths is None:
        return SimpleNamespace(http=None)
    return SimpleNamespace(
        http=SimpleNamespace(paths=[SimpleNamespace(path=path) for path in paths])
    )


def ing(
    ingress_name: str,
    namespace: str = "services",
    annotations: dict[str, str] | None = None,
    rules: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=ingress_name, namespace=namespace, annotations=annotations
        ),
        spec=SimpleNamespace(rules=rules),
    )


@pytest.fixture
def fake_k8s(monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    listed: list[SimpleNamespace] = []
    loaded: list[str] = []

    class ConfigException(Exception):
        pass

    config = ModuleType("kubernetes.config")
    config.ConfigException = ConfigException
    config.load_incluster_config = lambda: loaded.append("incluster")
    config.load_kube_config = lambda: loaded.append("kubeconfig")

    class NetworkingV1Api:
        def list_ingress_for_all_namespaces(self) -> SimpleNamespace:
            return SimpleNamespace(items=listed)

    client = ModuleType("kubernetes.client")
    client.NetworkingV1Api = NetworkingV1Api

    package = ModuleType("kubernetes")
    package.client = client
    package.config = config

    monkeypatch.setitem(sys.modules, "kubernetes", package)
    monkeypatch.setitem(sys.modules, "kubernetes.client", client)
    monkeypatch.setitem(sys.modules, "kubernetes.config", config)
    # module-level latch: reset so each test observes its own config loading
    monkeypatch.setattr(ingress_source, "_config_loaded", False)
    return SimpleNamespace(
        listed=listed, loaded=loaded, config=config, exception=ConfigException
    )


def test_first_rule_path_and_annotations_are_extracted(
    fake_k8s: SimpleNamespace,
) -> None:
    fake_k8s.listed.append(
        ing(
            "home",
            annotations={"kaapana.ai/ui.name": "Home"},
            rules=[rule(["/home", "/second"]), rule(["/other"])],
        )
    )
    (info,) = ingress_source._list_ingresses_blocking()
    assert (info.namespace, info.name) == ("services", "home")
    assert info.annotations == {"kaapana.ai/ui.name": "Home"}
    assert info.first_path == "/home"


def test_rules_without_http_or_paths_are_skipped(fake_k8s: SimpleNamespace) -> None:
    fake_k8s.listed.append(ing("app", rules=[rule(None), rule([]), rule(["/app"])]))
    (info,) = ingress_source._list_ingresses_blocking()
    assert info.first_path == "/app"


def test_ingress_without_any_usable_rule_has_no_first_path(
    fake_k8s: SimpleNamespace,
) -> None:
    fake_k8s.listed.extend([ing("none", rules=None), ing("empty", rules=[rule(None)])])
    assert [info.first_path for info in ingress_source._list_ingresses_blocking()] == [
        None,
        None,
    ]


def test_missing_annotations_become_an_empty_dict(fake_k8s: SimpleNamespace) -> None:
    fake_k8s.listed.append(ing("bare", annotations=None, rules=[rule(["/bare"])]))
    (info,) = ingress_source._list_ingresses_blocking()
    assert info.annotations == {}


def test_incluster_config_is_loaded_only_once(fake_k8s: SimpleNamespace) -> None:
    ingress_source._list_ingresses_blocking()
    ingress_source._list_ingresses_blocking()
    assert fake_k8s.loaded == ["incluster"]


def test_kube_config_is_the_fallback_outside_the_cluster(
    fake_k8s: SimpleNamespace, monkeypatch: pytest.MonkeyPatch
) -> None:
    def raise_config_exception() -> None:
        raise fake_k8s.exception("not in a cluster")

    monkeypatch.setattr(
        fake_k8s.config, "load_incluster_config", raise_config_exception
    )
    ingress_source._list_ingresses_blocking()
    assert fake_k8s.loaded == ["kubeconfig"]


def test_list_ingresses_awaits_the_blocking_client(fake_k8s: SimpleNamespace) -> None:
    fake_k8s.listed.append(ing("home", rules=[rule(["/home"])]))
    (info,) = asyncio.run(ingress_source.list_ingresses())
    assert info.name == "home"
