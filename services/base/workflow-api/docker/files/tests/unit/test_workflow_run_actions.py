"""
Unit tests for canceling workflow runs before they reach the engine.

Covers:
- Cancel of a CREATED run and the background submission that must skip it.
"""

import sys
from pathlib import Path

import pytest
from app import crud, schemas
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.api.v1.services import workflow_run_service as service
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent))

from test_workflow_cleanup import (  # noqa: E402,F401
    _ensure_workflow,
    _make_workflow_and_run,
    _patch_get_async_db_for_cleanup,
    _reset_dummy_adapter_state,
)

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
