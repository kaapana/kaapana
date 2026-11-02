"""
Concurrency tests for the row lock on workflow runs.

Each test blocks the first request inside an engine call and starts a second
request on another session while the first one holds the lock.
"""

import asyncio

import pytest
from app import crud, schemas
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.api.v1.services import workflow_run_service as service
from app.api.v1.services.errors import ConflictError, NotFoundError

BLOCKED = 0.5


class Gate:
    def __init__(self):
        self.entered = asyncio.Event()
        self.released = asyncio.Event()

    async def pass_through(self):
        self.entered.set()
        await self.released.wait()


async def _assert_waits(task: asyncio.Task) -> None:
    await asyncio.sleep(BLOCKED)
    assert not task.done(), "the second request did not wait for the lock"


@pytest.mark.asyncio
async def test_cancel_during_submission_waits_and_cancels_the_engine_run(session_factory, make_run, monkeypatch):
    run_id = await make_run(schemas.WorkflowRunStatus.CREATED, external_id=None)
    gate = Gate()
    canceled: list[str] = []

    async def _slow_submit(self, workflow_run, project_id):
        await gate.pass_through()
        return schemas.WorkflowRunUpdate(
            external_id="dummy::submitted", lifecycle_status=schemas.WorkflowRunStatus.PENDING
        )

    async def _record_cancel(self, external_id):
        canceled.append(external_id)
        return schemas.WorkflowRunStatus.CANCELED

    monkeypatch.setattr(DummyAdapter, "submit_workflow_run", _slow_submit)
    monkeypatch.setattr(DummyAdapter, "cancel_workflow_run", _record_cancel)

    async with session_factory() as setup, session_factory() as submit_db, session_factory() as cancel_db:
        workflow_run = service._workflow_run_to_schema(await crud.get_workflow_run(setup, filters={"id": run_id}))
        submission = asyncio.create_task(
            service._submit_workflow_run_to_engine(submit_db, workflow_run, DummyAdapter(), project_id="proj-123")
        )
        await gate.entered.wait()
        cancel = asyncio.create_task(service.cancel_workflow_run(cancel_db, run_id))
        await _assert_waits(cancel)

        gate.released.set()
        await submission
        result = await cancel

    assert canceled == ["dummy::submitted"]
    assert result.lifecycle_status == schemas.WorkflowRunStatus.CANCELED
    assert result.external_id == "dummy::submitted"


@pytest.mark.asyncio
async def test_submission_after_a_cancel_skips_the_engine(session_factory, make_run, monkeypatch):
    run_id = await make_run(schemas.WorkflowRunStatus.CREATED, external_id=None)
    submitted: list[int] = []

    async def _record_submit(self, workflow_run, project_id):
        submitted.append(workflow_run.id)
        return schemas.WorkflowRunUpdate(external_id="never", lifecycle_status=schemas.WorkflowRunStatus.PENDING)

    monkeypatch.setattr(DummyAdapter, "submit_workflow_run", _record_submit)

    async with session_factory() as setup, session_factory() as submit_db, session_factory() as cancel_db:
        workflow_run = service._workflow_run_to_schema(await crud.get_workflow_run(setup, filters={"id": run_id}))
        await service.cancel_workflow_run(cancel_db, run_id)
        await service._submit_workflow_run_to_engine(submit_db, workflow_run, DummyAdapter(), project_id="proj-123")

    async with session_factory() as check:
        db_run = await crud.get_workflow_run(check, filters={"id": run_id})
    assert submitted == []
    assert db_run.lifecycle_status == schemas.WorkflowRunStatus.CANCELED
    assert db_run.external_id is None


@pytest.mark.asyncio
async def test_clean_during_delete_waits_and_finds_no_run(session_factory, make_run, monkeypatch):
    run_id = await make_run(schemas.WorkflowRunStatus.ERROR)
    gate = Gate()

    async def _slow_clean(self, external_id, project_id):
        await gate.pass_through()

    monkeypatch.setattr(DummyAdapter, "clean_workflow_run_data", _slow_clean)

    async with session_factory() as delete_db, session_factory() as clean_db:
        delete = asyncio.create_task(service.delete_workflow_run(delete_db, run_id))
        await gate.entered.wait()
        clean = asyncio.create_task(service.trigger_cleanup(clean_db, run_id))
        await _assert_waits(clean)

        gate.released.set()
        await delete
        with pytest.raises(NotFoundError):
            await clean

    assert DummyAdapter.was_deleted("dummy::run-1")


@pytest.mark.asyncio
async def test_delete_during_retry_waits_and_sees_the_restarted_run(session_factory, make_run, monkeypatch):
    run_id = await make_run(schemas.WorkflowRunStatus.ERROR)
    gate = Gate()

    async def _slow_retry(self, external_id):
        await gate.pass_through()
        return schemas.WorkflowRunStatus.PENDING

    monkeypatch.setattr(DummyAdapter, "retry_workflow_run", _slow_retry)

    async with session_factory() as retry_db, session_factory() as delete_db:
        retry = asyncio.create_task(service.retry_workflow_run(retry_db, run_id))
        await gate.entered.wait()
        delete = asyncio.create_task(service.delete_workflow_run(delete_db, run_id))
        await _assert_waits(delete)

        gate.released.set()
        await retry
        with pytest.raises(ConflictError, match="Cancel the run first"):
            await delete

    assert not DummyAdapter.was_deleted("dummy::run-1")


@pytest.mark.asyncio
async def test_a_request_that_waits_too_long_for_the_lock_answers_409(session_factory, make_run, monkeypatch):
    run_id = await make_run(schemas.WorkflowRunStatus.RUNNING)
    monkeypatch.setattr(service, "RUN_LOCK_TIMEOUT", "200ms")

    async with session_factory() as holder, session_factory() as cancel_db:
        await crud.lock_workflow_run(holder, run_id, "30s")
        with pytest.raises(ConflictError, match="Another request is changing this workflow run"):
            await service.cancel_workflow_run(cancel_db, run_id)
        await holder.rollback()
