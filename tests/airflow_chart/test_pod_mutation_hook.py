"""The scheduler's pod_mutation_hook applies its registry-probe result to the worker
pod's own containers (kaapana#2149) and leaves the pod alone when the helper is missing.

Executes the Python embedded in the airflow chart's configmap; needs Airflow and the
kubernetes client from tests/requirements.txt.
"""

import importlib
import sys
import types
from pathlib import Path

import pytest
import yaml

airflow = pytest.importorskip("airflow")

CONFIGMAP = (
    Path(__file__).resolve().parents[2]
    / "services/flow/airflow/airflow-chart/templates"
    / "configmap_airflow_local_settings.yaml"
)
HELPER_MODULE = "kaapana.blueprints.kaapana_registry"


@pytest.fixture
def client(monkeypatch):
    # tests/operators/utils.py replaces sys.modules["kubernetes*"] and ["requests"] with
    # MagicMocks when its modules are collected; the hook needs the real client models,
    # whose import chain reads requests.__version__.
    mocked = ("kubernetes", "requests")
    for name in [m for m in sys.modules if m.split(".")[0] in mocked]:
        monkeypatch.delitem(sys.modules, name)
    return importlib.import_module("kubernetes.client")


@pytest.fixture
def hook(client, monkeypatch):
    # The only Helm expression in the file is a quoted namespace; the YAML parses as is.
    source = yaml.safe_load(CONFIGMAP.read_text())["data"]["airflow_local_settings.py"]
    module = types.ModuleType("airflow_local_settings_under_test")
    exec(compile(source, str(CONFIGMAP), "exec"), module.__dict__)
    monkeypatch.setenv("PLATFORM_PREFIX", "kaapana")
    monkeypatch.setenv("DEFAULT_REGISTRY", "registry.example.com/kaapana")
    monkeypatch.setenv("PULL_POLICY_IMAGES", "Always")
    # No database and no log-streaming threads in the test.
    module.get_dagrun_from_pod = lambda pod: None
    module.LogStreamerService = types.SimpleNamespace(
        get_instance=lambda: types.SimpleNamespace(
            start=lambda: None, submit=lambda **kwargs: None
        )
    )
    return module


def _fake_helper(monkeypatch, decision):
    """Stands in for the plugin's kaapana_registry; records what the hook asked."""
    helper = types.ModuleType(HELPER_MODULE)
    helper.asked = []

    def effective_pull_policy(configured, registry):
        helper.asked.append((configured, registry))
        return decision

    helper.effective_pull_policy = effective_pull_policy
    for name in ("kaapana", "kaapana.blueprints"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    monkeypatch.setitem(sys.modules, HELPER_MODULE, helper)
    return helper


def _worker_pod(client):
    return client.V1Pod(
        metadata=client.V1ObjectMeta(name="worker", labels={}),
        spec=client.V1PodSpec(
            init_containers=[
                client.V1Container(name="sync-dags-plugins", image_pull_policy="Always")
            ],
            containers=[
                client.V1Container(
                    name="base",
                    image_pull_policy="Always",
                    env=[client.V1EnvVar(name="PULL_POLICY_IMAGES", value="Always")],
                )
            ],
        ),
    )


def test_hook_applies_probe_result_to_the_worker_containers(
    client, hook, monkeypatch
):
    helper = _fake_helper(monkeypatch, decision="IfNotPresent")
    pod = _worker_pod(client)

    hook.pod_mutation_hook(pod)

    assert helper.asked == [("Always", "registry.example.com/kaapana")]
    assert pod.spec.init_containers[0].image_pull_policy == "IfNotPresent"
    assert pod.spec.containers[0].image_pull_policy == "IfNotPresent"
    # The operators inside decide for their processing containers themselves.
    assert pod.spec.containers[0].env[0].value == "Always"


def test_hook_keeps_always_while_registry_answers(client, hook, monkeypatch):
    _fake_helper(monkeypatch, decision="Always")
    pod = _worker_pod(client)

    hook.pod_mutation_hook(pod)

    assert pod.spec.containers[0].image_pull_policy == "Always"


def test_hook_writes_only_the_fallback(client, hook, monkeypatch):
    # A task's pod_override may carry its own policy; while the registry answers the
    # hook does not touch it.
    _fake_helper(monkeypatch, decision="Always")
    pod = _worker_pod(client)
    pod.spec.containers[0].image_pull_policy = "Never"

    hook.pod_mutation_hook(pod)

    assert pod.spec.containers[0].image_pull_policy == "Never"


def test_hook_leaves_pod_unchanged_when_helper_import_fails(
    client, hook, monkeypatch, caplog
):
    # kaapana/blueprints/__init__.py runs on import and can fail with more than an
    # ImportError; pod creation must survive that too.
    class Failing:
        def find_spec(self, name, path=None, target=None):
            if name == HELPER_MODULE:
                raise KeyError("PLATFORM_PREFIX")
            return None

    for name in ("kaapana", "kaapana.blueprints"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules["kaapana.blueprints"].__path__ = []
    monkeypatch.delitem(sys.modules, HELPER_MODULE, raising=False)
    monkeypatch.setattr(sys, "meta_path", [Failing()] + sys.meta_path)
    pod = _worker_pod(client)

    hook.pod_mutation_hook(pod)

    assert pod.spec.containers[0].image_pull_policy == "Always"
    assert pod.metadata.namespace == "kaapana-project-admin"
    assert any("PLATFORM_PREFIX" in r.message for r in caplog.records)


def test_hook_leaves_pod_unchanged_without_helper(client, hook, monkeypatch, caplog):
    # An older plugin without kaapana_registry must not break pod creation.
    monkeypatch.setitem(sys.modules, HELPER_MODULE, None)
    pod = _worker_pod(client)

    hook.pod_mutation_hook(pod)
    hook.pod_mutation_hook(pod)

    assert pod.spec.containers[0].image_pull_policy == "Always"
    assert pod.metadata.namespace == "kaapana-project-admin"
    assert sum("kaapana_registry" in r.message for r in caplog.records) == 1
