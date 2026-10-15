"""
Unit tests for deleting workflow runs and for canceling runs before they reach the engine.

Covers:
- DELETE /v1/workflow-runs/{id}: only finished runs; removes data, engine run and records.
- Cancel of a CREATED run and the background submission that must skip it.
"""

import sys
from pathlib import Path

import pytest
from app import crud, models, schemas
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.api.v1.services import workflow_run_service as service
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent))

from test_workflow_cleanup import (  # noqa: E402,F401
    _ensure_workflow,
    _make_workflow_and_run,
    _patch_get_async_db_for_cleanup,
    _reset_dummy_adapter_state,
)


async def _add_task_run(session: AsyncSession, run: models.WorkflowRun) -> None:
    task = (await session.execute(select(models.Task).where(models.Task.title == "dummy-task-1"))).scalars().first()
    session.add(models.TaskRun(task_id=task.id, workflow_run_id=run.id, external_id=f"{run.external_id}::t1"))
    await session.commit()


async def _count(session: AsyncSession, model, **where) -> int:
    stmt = select(func.count()).select_from(model)
    for key, value in where.items():
        stmt = stmt.where(getattr(model, key) == value)
    return (await session.execute(stmt)).scalar_one()


# ============================================================
# DELETE /v1/workflow-runs/{id}
# ============================================================


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_finished_run_removes_data_engine_run_and_records(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.ERROR)
    run_id, external_id = run.id, run.external_id
    await _add_task_run(session, run)

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 204, response.text
    assert DummyAdapter.was_cleaned(external_id)
    assert DummyAdapter.was_deleted(external_id)
    session.expire_all()
    assert await crud.get_workflow_run(session, filters={"id": run_id}) is None
    assert await _count(session, models.TaskRun, workflow_run_id=run_id) == 0
    assert await _count(session, models.Label, key=crud.PROJECT_ID_LABEL_KEY) == 1
    assert (await client.get(f"/v1/workflow-runs/{run_id}")).status_code == 404


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_cleaned_run_does_not_clean_again(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.COMPLETED)
    run_id, external_id = run.id, run.external_id
    await crud.update_workflow_run_cleanup_state(session, run_id, schemas.CleanupStatus.CLEANED)

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 204, response.text
    assert not DummyAdapter.was_cleaned(external_id)
    assert DummyAdapter.was_deleted(external_id)


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_run_that_never_reached_the_engine(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.CANCELED, external_id=None)
    run_id = run.id

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 204, response.text
    session.expire_all()
    assert await crud.get_workflow_run(session, filters={"id": run_id}) is None


@pytest.mark.DELETE
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "lifecycle",
    [
        schemas.WorkflowRunStatus.CREATED,
        schemas.WorkflowRunStatus.PENDING,
        schemas.WorkflowRunStatus.SCHEDULED,
        schemas.WorkflowRunStatus.RUNNING,
    ],
)
async def test_delete_active_run_is_rejected(session: AsyncSession, client: AsyncClient, lifecycle):
    run = await _make_workflow_and_run(session, lifecycle=lifecycle)
    run_id, external_id = run.id, run.external_id

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 409
    assert "Cancel the run first" in response.json()["detail"]
    assert not DummyAdapter.was_deleted(external_id)


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_while_cleanup_runs_is_rejected(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.COMPLETED)
    run_id = run.id
    await crud.update_workflow_run_cleanup_state(session, run_id, schemas.CleanupStatus.RUNNING)

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 409


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_keeps_the_run_when_its_data_cannot_be_deleted(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.ERROR)
    run_id, external_id = run.id, run.external_id
    DummyAdapter.make_cleanup_raise(external_id)

    response = await client.delete(f"/v1/workflow-runs/{run_id}")

    assert response.status_code == 503
    assert not DummyAdapter.was_deleted(external_id)
    session.expire_all()
    assert await crud.get_workflow_run(session, filters={"id": run_id}) is not None


@pytest.mark.DELETE
@pytest.mark.asyncio
async def test_delete_missing_run_returns_404(client: AsyncClient):
    assert (await client.delete("/v1/workflow-runs/99999")).status_code == 404


# ============================================================
# Cancel before the engine has the run
# ============================================================


async def _schema(session: AsyncSession, run_id: int) -> schemas.WorkflowRun:
    db_run = await crud.get_workflow_run(session, filters={"id": run_id})
    assert db_run is not None
    return service._workflow_run_to_schema(db_run)


@pytest.mark.asyncio
async def test_submission_skips_a_run_canceled_before_it_started(session: AsyncSession, monkeypatch):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.CREATED, external_id=None)
    run_id = run.id
    workflow_run = await _schema(session, run_id)
    await service.cancel_workflow_run(session, run_id)

    submitted: list[int] = []

    async def _record_submit(self, wf_run, project_id):
        submitted.append(wf_run.id)
        return schemas.WorkflowRunUpdate(external_id="never", lifecycle_status=schemas.WorkflowRunStatus.PENDING)

    monkeypatch.setattr(DummyAdapter, "submit_workflow_run", _record_submit)
    await service._submit_workflow_run_to_engine(session, workflow_run, DummyAdapter(), project_id="proj-123")

    assert submitted == []
    session.expire_all()
    db_run = await crud.get_workflow_run(session, filters={"id": run_id})
    assert db_run.lifecycle_status == schemas.WorkflowRunStatus.CANCELED
    assert db_run.external_id is None


@pytest.mark.asyncio
async def test_a_run_canceled_during_submission_is_canceled_in_the_engine(session: AsyncSession, monkeypatch):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.CREATED, external_id=None)
    run_id = run.id
    workflow_run = await _schema(session, run_id)

    async def _submit_while_user_cancels(self, wf_run, project_id):
        await crud.update_workflow_run(
            session, wf_run.id, schemas.WorkflowRunUpdate(lifecycle_status=schemas.WorkflowRunStatus.CANCELED)
        )
        return schemas.WorkflowRunUpdate(external_id="late-ext", lifecycle_status=schemas.WorkflowRunStatus.PENDING)

    canceled: list[str] = []

    async def _record_cancel(self, external_id):
        canceled.append(external_id)
        return schemas.WorkflowRunStatus.CANCELED

    monkeypatch.setattr(DummyAdapter, "submit_workflow_run", _submit_while_user_cancels)
    monkeypatch.setattr(DummyAdapter, "cancel_workflow_run", _record_cancel)
    await service._submit_workflow_run_to_engine(session, workflow_run, DummyAdapter(), project_id="proj-123")

    assert canceled == ["late-ext"]
    session.expire_all()
    db_run = await crud.get_workflow_run(session, filters={"id": run_id})
    assert db_run.lifecycle_status == schemas.WorkflowRunStatus.CANCELED
    assert db_run.external_id == "late-ext"


@pytest.mark.asyncio
async def test_submission_of_a_created_run_still_works(session: AsyncSession):
    run = await _make_workflow_and_run(session, lifecycle=schemas.WorkflowRunStatus.CREATED, external_id=None)
    run_id = run.id
    workflow_run = await _schema(session, run_id)

    await service._submit_workflow_run_to_engine(session, workflow_run, DummyAdapter(), project_id="proj-123")

    session.expire_all()
    db_run = await crud.get_workflow_run(session, filters={"id": run_id})
    assert db_run.lifecycle_status == schemas.WorkflowRunStatus.PENDING
    assert db_run.external_id is not None
