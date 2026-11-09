"""
Unit tests for the Airflow requests behind retry and delete of a workflow run.
"""

import pytest
from app.adapters.adapters.airflow_adapter import AirflowPluginAdapter

EXTERNAL_ID = "my-dag::manual__2026-10-05"


@pytest.fixture
def adapter(tmp_path, monkeypatch) -> AirflowPluginAdapter:
    monkeypatch.setenv("AIRFLOW_DAG_FOLDER", str(tmp_path))
    return AirflowPluginAdapter()


@pytest.fixture
def requests(adapter, monkeypatch) -> list[tuple[str, str, dict]]:
    calls: list[tuple[str, str, dict]] = []

    async def _record(method, endpoint, json={}, accepted_content_types=("application/json",)):
        calls.append((method, endpoint, json))
        return {}

    monkeypatch.setattr(adapter, "_request", _record)
    return calls


@pytest.mark.asyncio
async def test_retry_clears_only_failed_tasks_of_the_run(adapter, requests):
    dag_id, run_id = adapter._parse_composite_id(EXTERNAL_ID)

    await adapter.retry_workflow_run(EXTERNAL_ID)

    assert requests == [
        (
            "POST",
            f"/dags/{dag_id}/clearTaskInstances",
            {
                "dag_run_id": run_id,
                "dry_run": False,
                "only_failed": True,
                "include_downstream": True,
                "reset_dag_runs": True,
            },
        )
    ]


@pytest.mark.asyncio
async def test_delete_removes_the_dag_run(adapter, requests):
    dag_id, run_id = adapter._parse_composite_id(EXTERNAL_ID)

    await adapter.delete_workflow_run(EXTERNAL_ID)

    assert requests == [("DELETE", f"/dags/{dag_id}/dagRuns/{run_id}", {})]


@pytest.mark.asyncio
async def test_delete_of_an_unknown_dag_run_is_a_no_op(adapter, monkeypatch):
    async def _not_found(method, endpoint, json={}, accepted_content_types=("application/json",)):
        raise FileNotFoundError(endpoint)

    monkeypatch.setattr(adapter, "_request", _not_found)

    await adapter.delete_workflow_run(EXTERNAL_ID)
