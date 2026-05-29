"""
Filesystem tests for AirflowPluginAdapter cleanup methods.

The DummyAdapter unit tests cover the cleanup state machine end-to-end but
do not exercise the actual deletion. This file points the AirflowPluginAdapter
at a tmp_path data directory and verifies that clean_workflow_run_data,
get_workflow_run_data_size, and is_workflow_run_data_clean behave correctly
against real files and directories.
"""

from pathlib import Path

import pytest

from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter


@pytest.fixture
def adapter(tmp_path, monkeypatch) -> AirflowPluginAdapter:
    """An AirflowPluginAdapter rooted under tmp_path.

    Sets both AIRFLOW_DAG_FOLDER (needed at construction time so the operator-
    staging step has somewhere to land) and AIRFLOW_WORKFLOW_DATA_DIR.
    """
    dags = tmp_path / "dags"
    data = tmp_path / "data"
    dags.mkdir()
    data.mkdir()
    monkeypatch.setenv("AIRFLOW_DAG_FOLDER", str(dags))
    monkeypatch.setenv("AIRFLOW_WORKFLOW_DATA_DIR", str(data))
    return AirflowPluginAdapter()


def _seed_run_dir(adapter: AirflowPluginAdapter, run_id: str) -> Path:
    target = adapter.airflow_workflow_data_dir / run_id
    target.mkdir(parents=True, exist_ok=True)
    (target / "out.bin").write_bytes(b"x" * 1024)
    sub = target / "task_a" / "channel_1"
    sub.mkdir(parents=True)
    (sub / "more.bin").write_bytes(b"y" * 256)
    return target


@pytest.mark.asyncio
async def test_data_size_walks_tree(adapter: AirflowPluginAdapter):
    target = _seed_run_dir(adapter, "run-1")
    external_id = f"any-dag::run-1"

    size = await adapter.get_workflow_run_data_size(external_id)
    assert size == 1024 + 256
    assert target.exists()


@pytest.mark.asyncio
async def test_data_size_zero_when_missing(adapter: AirflowPluginAdapter):
    size = await adapter.get_workflow_run_data_size("any-dag::does-not-exist")
    assert size == 0


@pytest.mark.asyncio
async def test_is_clean_true_when_missing(adapter: AirflowPluginAdapter):
    assert await adapter.is_workflow_run_data_clean("any-dag::missing") is True


@pytest.mark.asyncio
async def test_is_clean_false_when_data_present(adapter: AirflowPluginAdapter):
    _seed_run_dir(adapter, "run-2")
    assert await adapter.is_workflow_run_data_clean("any-dag::run-2") is False


@pytest.mark.asyncio
async def test_clean_removes_directory_tree(adapter: AirflowPluginAdapter):
    target = _seed_run_dir(adapter, "run-3")
    external_id = "any-dag::run-3"

    await adapter.clean_workflow_run_data(external_id)

    assert not target.exists()
    assert await adapter.is_workflow_run_data_clean(external_id) is True
    assert await adapter.get_workflow_run_data_size(external_id) == 0


@pytest.mark.asyncio
async def test_clean_is_idempotent(adapter: AirflowPluginAdapter):
    external_id = "any-dag::never-existed"
    # Should not raise even though the directory was never created.
    await adapter.clean_workflow_run_data(external_id)
    await adapter.clean_workflow_run_data(external_id)


@pytest.mark.asyncio
async def test_clean_does_not_touch_sibling_runs(adapter: AirflowPluginAdapter):
    a = _seed_run_dir(adapter, "run-a")
    b = _seed_run_dir(adapter, "run-b")

    await adapter.clean_workflow_run_data("any-dag::run-a")

    assert not a.exists()
    assert b.exists()
    assert (b / "out.bin").exists()
