"""
Filesystem tests for AirflowPluginAdapter cleanup methods.

After the host-path -> PVC migration (MR 970) a run's data lives in TWO stores:

  1. the local scheduler/pkl folder (services-namespace workflows PVC, mounted
     into workflow-api at AIRFLOW_WORKFLOW_DATA_DIR), and
  2. the project-namespace ``workflow-data-pv-claim`` PVC, reachable only via the
     project's ``project-runtime`` service.

These tests point the adapter at a tmp_path for store #1 and back store #2 with a
second tmp_path behind a fake ``_project_runtime_request`` that implements the same
delete/usage contract as the real service. ``_fetch_project`` is stubbed so the
adapter resolves a namespace without talking to AII.
"""

import shutil
from pathlib import Path

import pytest

from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter

PROJECT_ID = "proj-123"
NAMESPACE = "kaapana-project-proj123"


@pytest.fixture
def pvc_root(tmp_path) -> Path:
    """Simulated mount root of the project-namespace workflow-data PVC."""
    root = tmp_path / "pvc"
    root.mkdir()
    return root


@pytest.fixture
def adapter(tmp_path, pvc_root, monkeypatch) -> AirflowPluginAdapter:
    """An AirflowPluginAdapter whose two data stores are tmp dirs.

    Store #1 (local pkl folder) -> tmp_path/data via AIRFLOW_WORKFLOW_DATA_DIR.
    Store #2 (project PVC) -> ``pvc_root`` via a fake project-runtime client.
    """
    dags = tmp_path / "dags"
    data = tmp_path / "data"
    dags.mkdir()
    data.mkdir()
    monkeypatch.setenv("AIRFLOW_DAG_FOLDER", str(dags))
    monkeypatch.setenv("AIRFLOW_WORKFLOW_DATA_DIR", str(data))
    adapter = AirflowPluginAdapter()

    async def _fake_fetch_project(project_id: str) -> dict:
        assert project_id == PROJECT_ID
        return {"id": project_id, "kubernetes_namespace": NAMESPACE}

    async def _fake_pr_request(namespace, method, endpoint, json=None):
        # The real adapter targets the project's runtime in its namespace.
        assert namespace == NAMESPACE
        sub_path = (json or {})["sub_path"]
        target = pvc_root / sub_path
        if endpoint == "/filesystem/delete":
            if not target.exists():
                return {"deleted": False}
            shutil.rmtree(target)
            return {"deleted": True}
        if endpoint == "/filesystem/usage":
            if not target.exists():
                return {"exists": False, "empty": True, "size_bytes": 0}
            empty = target.is_dir() and not any(target.iterdir())
            total = sum(p.stat().st_size for p in target.rglob("*") if p.is_file())
            return {"exists": True, "empty": empty, "size_bytes": total}
        raise AssertionError(f"unexpected project-runtime endpoint {endpoint}")

    monkeypatch.setattr(adapter, "_fetch_project", _fake_fetch_project)
    monkeypatch.setattr(adapter, "_project_runtime_request", _fake_pr_request)
    return adapter


def _seed_local(adapter: AirflowPluginAdapter, run_id: str) -> Path:
    """Seed store #1 (local pkl folder) with a task_run pkl + a channel dir."""
    target = adapter.airflow_workflow_data_dir / run_id
    target.mkdir(parents=True, exist_ok=True)
    (target / "task_run-task_a.pkl").write_bytes(b"x" * 1024)
    sub = target / "task_a" / "channel_1"
    sub.mkdir(parents=True)
    (sub / "more.bin").write_bytes(b"y" * 256)
    return target


def _seed_pvc(pvc_root: Path, run_id: str) -> Path:
    """Seed store #2 (project PVC) with the actual processing output."""
    target = pvc_root / run_id
    out = target / "task_a" / "channel_1"
    out.mkdir(parents=True)
    (out / "result.dcm").write_bytes(b"z" * 4096)
    return target


@pytest.mark.asyncio
async def test_data_size_sums_both_stores(adapter, pvc_root):
    _seed_local(adapter, "run-1")
    _seed_pvc(pvc_root, "run-1")

    size = await adapter.get_workflow_run_data_size("any-dag::run-1", PROJECT_ID)
    # local: 1024 + 256, pvc: 4096
    assert size == (1024 + 256) + 4096


@pytest.mark.asyncio
async def test_data_size_zero_when_missing(adapter):
    size = await adapter.get_workflow_run_data_size(
        "any-dag::does-not-exist", PROJECT_ID
    )
    assert size == 0


@pytest.mark.asyncio
async def test_is_clean_true_when_both_missing(adapter):
    assert (
        await adapter.is_workflow_run_data_clean("any-dag::missing", PROJECT_ID) is True
    )


@pytest.mark.asyncio
async def test_is_clean_false_when_only_local_present(adapter):
    _seed_local(adapter, "run-2")
    assert (
        await adapter.is_workflow_run_data_clean("any-dag::run-2", PROJECT_ID) is False
    )


@pytest.mark.asyncio
async def test_is_clean_false_when_only_pvc_present(adapter, pvc_root):
    _seed_pvc(pvc_root, "run-2b")
    assert (
        await adapter.is_workflow_run_data_clean("any-dag::run-2b", PROJECT_ID) is False
    )


@pytest.mark.asyncio
async def test_clean_removes_both_stores(adapter, pvc_root):
    local = _seed_local(adapter, "run-3")
    pvc = _seed_pvc(pvc_root, "run-3")
    external_id = "any-dag::run-3"

    await adapter.clean_workflow_run_data(external_id, PROJECT_ID)

    assert not local.exists()
    assert not pvc.exists()
    assert await adapter.is_workflow_run_data_clean(external_id, PROJECT_ID) is True
    assert await adapter.get_workflow_run_data_size(external_id, PROJECT_ID) == 0


@pytest.mark.asyncio
async def test_clean_is_idempotent(adapter):
    external_id = "any-dag::never-existed"
    # Should not raise even though neither store was ever created.
    await adapter.clean_workflow_run_data(external_id, PROJECT_ID)
    await adapter.clean_workflow_run_data(external_id, PROJECT_ID)


@pytest.mark.asyncio
async def test_clean_does_not_touch_sibling_runs(adapter, pvc_root):
    a_local = _seed_local(adapter, "run-a")
    a_pvc = _seed_pvc(pvc_root, "run-a")
    b_local = _seed_local(adapter, "run-b")
    b_pvc = _seed_pvc(pvc_root, "run-b")

    await adapter.clean_workflow_run_data("any-dag::run-a", PROJECT_ID)

    assert not a_local.exists()
    assert not a_pvc.exists()
    assert b_local.exists()
    assert b_pvc.exists()


@pytest.mark.asyncio
async def test_clean_uses_run_id_as_pvc_sub_path(adapter, monkeypatch):
    """The PVC delete must target exactly the run_id sub-path, never above it."""
    seen = {}

    async def _record(namespace, method, endpoint, json=None):
        seen[endpoint] = (namespace, json)
        return {"deleted": False}

    monkeypatch.setattr(adapter, "_project_runtime_request", _record)
    await adapter.clean_workflow_run_data("my-dag::run-xyz", PROJECT_ID)

    assert seen["/filesystem/delete"] == (NAMESPACE, {"sub_path": "run-xyz"})


@pytest.mark.asyncio
async def test_missing_namespace_raises(adapter, monkeypatch):
    async def _no_ns(project_id):
        return {"id": project_id}

    monkeypatch.setattr(adapter, "_fetch_project", _no_ns)
    with pytest.raises(RuntimeError):
        await adapter.clean_workflow_run_data("any-dag::run-1", PROJECT_ID)
