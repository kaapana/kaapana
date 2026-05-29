"""
Unit tests for policy-driven workflow run cleanup (issue #2202).

Covers:
- Schema: CleanupPolicy / CleanupStatus round-trip through Pydantic models.
- Policy matrix: _should_clean across (policy x terminal status).
- Sync-driven flow: status transition into a terminal state dispatches
  cleanup; cleanup_status walks NOT_REQUIRED → PENDING → CLEANED.
- Manual /clean endpoint: 202 from NOT_REQUIRED/FAILED, 409 while
  PENDING/RUNNING, 200 once CLEANED.
- /data-size endpoint.
- Concurrency: only one of two racing claim attempts wins.
- Edge case: terminal state with external_id=None marks CLEANED.
"""

import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app import crud, models, schemas
from app.adapters.adapters.dummy_adapter import DummyAdapter
from app.api.v1.services import workflow_run_service as service


@pytest.fixture(autouse=True)
def _reset_dummy_adapter_state(monkeypatch):
    DummyAdapter.reset_statuses()
    DummyAdapter.reset_cleanup_state()

    # The DummyAdapter's stock get_workflow_run_task_runs returns task_runs
    # for "dummy-task-1" / "dummy-task-2"; the sync path's task_run upsert
    # has a pre-existing bug (subscripts TaskRunStatus by the enum itself
    # rather than its name). Out of scope for #2202 — short-circuit it here.
    async def _empty_task_runs(self, _external_id):
        return []

    monkeypatch.setattr(DummyAdapter, "get_workflow_run_task_runs", _empty_task_runs)

    yield
    DummyAdapter.reset_statuses()
    DummyAdapter.reset_cleanup_state()


@pytest_asyncio.fixture(autouse=True)
async def _patch_get_async_db_for_cleanup(monkeypatch, session: AsyncSession):
    """Give the cleanup task its own session bound to the test engine.

    `_run_cleanup` opens a session via `get_async_db()` because it must not
    share a session with its caller (SQLAlchemy sessions are not safe
    for concurrent use). In tests the global async_session is bound to a
    different engine than the per-test session fixture — we override the
    service-module reference so cleanup work opens a fresh session on
    the same in-memory engine (StaticPool → shared connection → same data).
    """
    async_engine = session.sync_session.bind  # AsyncEngine's sync facade
    # Reach back to the AsyncEngine through the sync engine's _proxied attr.
    # Simpler: pytest's session fixture leaks the engine via session.bind.
    bind = session.bind
    factory = async_sessionmaker(bind=bind, expire_on_commit=False)

    async def _override():
        async with factory() as s:
            yield s

    monkeypatch.setattr(service, "get_async_db", _override)
    yield


# ============================================================
# Schema round-trip
# ============================================================


def test_workflow_run_create_default_cleanup_policy_is_on_success():
    payload = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(id=uuid.uuid4(), title="w", increment=1)
    )
    assert payload.cleanup_policy == schemas.CleanupPolicy.ON_SUCCESS


def test_workflow_run_create_accepts_explicit_policy():
    payload = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(id=uuid.uuid4(), title="w", increment=1),
        cleanup_policy=schemas.CleanupPolicy.NEVER,
    )
    assert payload.cleanup_policy == schemas.CleanupPolicy.NEVER


def test_cleanup_status_enum_values():
    assert schemas.CleanupStatus("not_required") == schemas.CleanupStatus.NOT_REQUIRED
    assert schemas.CleanupStatus("pending") == schemas.CleanupStatus.PENDING
    assert schemas.CleanupStatus("running") == schemas.CleanupStatus.RUNNING
    assert schemas.CleanupStatus("cleaned") == schemas.CleanupStatus.CLEANED
    assert schemas.CleanupStatus("failed") == schemas.CleanupStatus.FAILED


# ============================================================
# Policy matrix
# ============================================================


@pytest.mark.parametrize(
    "policy,status,expected",
    [
        (schemas.CleanupPolicy.NEVER, schemas.WorkflowRunStatus.COMPLETED, False),
        (schemas.CleanupPolicy.NEVER, schemas.WorkflowRunStatus.ERROR, False),
        (schemas.CleanupPolicy.NEVER, schemas.WorkflowRunStatus.CANCELED, False),
        (schemas.CleanupPolicy.NEVER, schemas.WorkflowRunStatus.RUNNING, False),
        (schemas.CleanupPolicy.ON_SUCCESS, schemas.WorkflowRunStatus.COMPLETED, True),
        (schemas.CleanupPolicy.ON_SUCCESS, schemas.WorkflowRunStatus.ERROR, False),
        (schemas.CleanupPolicy.ON_SUCCESS, schemas.WorkflowRunStatus.CANCELED, False),
        (schemas.CleanupPolicy.ON_SUCCESS, schemas.WorkflowRunStatus.RUNNING, False),
        (schemas.CleanupPolicy.ALWAYS, schemas.WorkflowRunStatus.COMPLETED, True),
        (schemas.CleanupPolicy.ALWAYS, schemas.WorkflowRunStatus.ERROR, True),
        (schemas.CleanupPolicy.ALWAYS, schemas.WorkflowRunStatus.CANCELED, True),
        (schemas.CleanupPolicy.ALWAYS, schemas.WorkflowRunStatus.RUNNING, False),
    ],
)
def test_should_clean_matrix(policy, status, expected):
    assert service._should_clean(policy, status) is expected


# ============================================================
# Helpers
# ============================================================


async def _ensure_workflow(session: AsyncSession) -> models.WorkflowRevision:
    """Get-or-create the canonical workflow revision used by the cleanup tests.

    Includes the two Task rows that DummyAdapter.get_workflow_run_task_runs
    always reports, so the periodic sync can upsert task runs without
    hitting "task not found" errors.
    """
    existing = (
        await session.execute(
            select(models.WorkflowRevision)
            .join(models.Workflow)
            .where(models.Workflow.title == "cleanup-wf")
        )
    ).scalars().first()
    if existing:
        return existing

    workflow = models.Workflow(title="cleanup-wf", workflow_engine="dummy")
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    revision = models.WorkflowRevision(
        workflow_id=workflow.id,
        increment=1,
        definition="def",
    )
    session.add(revision)
    await session.commit()
    await session.refresh(revision)

    for title in ("dummy-task-1", "dummy-task-2"):
        session.add(
            models.Task(workflow_revision_id=revision.id, title=title, type="test")
        )
    await session.commit()
    return revision


async def _make_workflow_and_run(
    session: AsyncSession,
    *,
    policy: schemas.CleanupPolicy = schemas.CleanupPolicy.ON_SUCCESS,
    lifecycle: schemas.WorkflowRunStatus = schemas.WorkflowRunStatus.RUNNING,
    external_id: str | None = "test-extid::run-1",
) -> models.WorkflowRun:
    revision = await _ensure_workflow(session)
    run = models.WorkflowRun(
        workflow_revision_id=revision.id,
        external_id=external_id,
        lifecycle_status=lifecycle,
        cleanup_policy=policy,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)
    return run


async def _wait_for_cleanup(
    session: AsyncSession,
    run_id: int,
    target: schemas.CleanupStatus,
    timeout: float = 2.0,
) -> models.WorkflowRun:
    """Spin until the run's cleanup_status reaches `target` (or timeout).

    The cleanup task writes via its own session; the test session caches
    the row in its identity map, so we must expire it each iteration to
    pick up cross-session commits over the shared StaticPool connection.
    """
    deadline = asyncio.get_event_loop().time() + timeout
    last = None
    while True:
        session.expire_all()
        run = await crud.get_workflow_run(session, filters={"id": run_id})
        assert run is not None
        last = run.cleanup_status
        if last == target:
            return run
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError(
                f"Timed out waiting for cleanup_status={target.value}; got {last.value}"
            )
        await asyncio.sleep(0.05)


# ============================================================
# Sync-driven dispatch
# ============================================================


@pytest.mark.asyncio
async def test_sync_transition_to_completed_with_on_success_triggers_cleanup(
    session: AsyncSession,
):
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.ON_SUCCESS)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.COMPLETED)

    await service.sync_active_runs(session)

    cleaned = await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.CLEANED)
    assert cleaned.lifecycle_status == schemas.WorkflowRunStatus.COMPLETED
    assert cleaned.cleaned_at is not None
    assert DummyAdapter.was_cleaned(run.external_id)


@pytest.mark.asyncio
async def test_sync_transition_to_error_with_on_success_skips_cleanup(
    session: AsyncSession,
):
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.ON_SUCCESS)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.ERROR)

    await service.sync_active_runs(session)

    # Give the event loop a chance to dispatch anything that shouldn't fire.
    await asyncio.sleep(0.05)

    refreshed = await crud.get_workflow_run(session, filters={"id": run.id})
    assert refreshed is not None
    assert refreshed.lifecycle_status == schemas.WorkflowRunStatus.ERROR
    assert refreshed.cleanup_status == schemas.CleanupStatus.NOT_REQUIRED
    assert not DummyAdapter.was_cleaned(run.external_id)


@pytest.mark.asyncio
async def test_sync_transition_to_canceled_with_always_triggers_cleanup(
    session: AsyncSession,
):
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.ALWAYS)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.CANCELED)

    await service.sync_active_runs(session)
    cleaned = await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.CLEANED)
    assert cleaned.lifecycle_status == schemas.WorkflowRunStatus.CANCELED


@pytest.mark.asyncio
async def test_sync_transition_with_never_policy_skips_cleanup(session: AsyncSession):
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.NEVER)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.COMPLETED)

    await service.sync_active_runs(session)
    await asyncio.sleep(0.05)

    refreshed = await crud.get_workflow_run(session, filters={"id": run.id})
    assert refreshed is not None
    assert refreshed.cleanup_status == schemas.CleanupStatus.NOT_REQUIRED
    assert not DummyAdapter.was_cleaned(run.external_id)


@pytest.mark.asyncio
async def test_cleanup_failure_marks_failed(session: AsyncSession):
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.ALWAYS)
    DummyAdapter.make_cleanup_raise(run.external_id)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.COMPLETED)

    await service.sync_active_runs(session)
    failed = await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.FAILED)
    assert failed.cleaned_at is None


# ============================================================
# /clean endpoint
# ============================================================


@pytest.mark.asyncio
async def test_clean_endpoint_returns_202_and_cleans(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
    )

    resp = await client.post(f"/v1/workflow-runs/{run.id}/clean")
    assert resp.status_code == 202
    body = resp.json()
    assert body["cleanup_status"] in (
        schemas.CleanupStatus.PENDING.value,
        schemas.CleanupStatus.RUNNING.value,
        schemas.CleanupStatus.CLEANED.value,
    )

    await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.CLEANED)


@pytest.mark.asyncio
async def test_clean_endpoint_idempotent_when_already_cleaned(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
    )
    await crud.update_workflow_run_cleanup_state(
        session, run.id, schemas.CleanupStatus.CLEANED
    )

    resp = await client.post(f"/v1/workflow-runs/{run.id}/clean")
    assert resp.status_code == 200
    assert resp.json()["cleanup_status"] == schemas.CleanupStatus.CLEANED.value


@pytest.mark.asyncio
async def test_clean_endpoint_409_while_pending(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
    )
    await crud.update_workflow_run_cleanup_state(
        session, run.id, schemas.CleanupStatus.PENDING
    )

    resp = await client.post(f"/v1/workflow-runs/{run.id}/clean")
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_clean_endpoint_400_when_not_terminal(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.RUNNING,
    )

    resp = await client.post(f"/v1/workflow-runs/{run.id}/clean")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_clean_endpoint_404_when_missing(client: AsyncClient):
    resp = await client.post("/v1/workflow-runs/9999/clean")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_clean_endpoint_retries_from_failed(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
    )
    await crud.update_workflow_run_cleanup_state(
        session, run.id, schemas.CleanupStatus.FAILED
    )

    resp = await client.post(f"/v1/workflow-runs/{run.id}/clean")
    assert resp.status_code == 202

    await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.CLEANED)


# ============================================================
# /data-size endpoint
# ============================================================


@pytest.mark.asyncio
async def test_data_size_endpoint(session: AsyncSession, client: AsyncClient):
    run = await _make_workflow_and_run(session)
    DummyAdapter.set_data_size(run.external_id, 12345)

    resp = await client.get(f"/v1/workflow-runs/{run.id}/data-size")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "workflow_run_id": run.id,
        "size_bytes": 12345,
        "exists": True,
    }


@pytest.mark.asyncio
async def test_data_size_endpoint_no_external_id(
    session: AsyncSession, client: AsyncClient
):
    run = await _make_workflow_and_run(
        session,
        lifecycle=schemas.WorkflowRunStatus.ERROR,
        external_id=None,
    )

    resp = await client.get(f"/v1/workflow-runs/{run.id}/data-size")
    assert resp.status_code == 200
    body = resp.json()
    assert body == {
        "workflow_run_id": run.id,
        "size_bytes": 0,
        "exists": False,
    }


# ============================================================
# List filter
# ============================================================


@pytest.mark.asyncio
async def test_list_filter_by_cleanup_status(
    session: AsyncSession, client: AsyncClient
):
    failed = await _make_workflow_and_run(
        session,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
        external_id="extid::failed",
    )
    cleaned = await _make_workflow_and_run(
        session,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
        external_id="extid::cleaned",
    )
    await crud.update_workflow_run_cleanup_state(
        session, failed.id, schemas.CleanupStatus.FAILED
    )
    await crud.update_workflow_run_cleanup_state(
        session, cleaned.id, schemas.CleanupStatus.CLEANED
    )

    resp = await client.get("/v1/workflow-runs?cleanup_status=failed")
    assert resp.status_code == 200
    data = resp.json()
    ids = {item["id"] for item in data}
    assert failed.id in ids
    assert cleaned.id not in ids


# ============================================================
# Concurrency / edge cases
# ============================================================


@pytest.mark.asyncio
async def test_atomic_claim_only_succeeds_once(session: AsyncSession):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.ALWAYS,
        lifecycle=schemas.WorkflowRunStatus.COMPLETED,
    )

    first = await crud.claim_workflow_run_for_cleanup(
        session,
        run_id=run.id,
        allowed_from=[schemas.CleanupStatus.NOT_REQUIRED],
    )
    second = await crud.claim_workflow_run_for_cleanup(
        session,
        run_id=run.id,
        allowed_from=[schemas.CleanupStatus.NOT_REQUIRED],
    )

    assert first is True
    assert second is False


@pytest.mark.asyncio
async def test_list_endpoint_returns_fresh_lifecycle_after_cleanup_dispatch(
    session: AsyncSession, client: AsyncClient
):
    """Regression: the atomic UPDATE that dispatches cleanup bypasses the
    ORM identity map. Make sure callers that hold the ORM object see the
    new lifecycle_status after _apply_engine_status returns — otherwise
    the list endpoint returns stale data to the client.
    """
    run = await _make_workflow_and_run(session, policy=schemas.CleanupPolicy.ON_SUCCESS)
    DummyAdapter.set_status(run.external_id, schemas.WorkflowRunStatus.COMPLETED)

    resp = await client.get("/v1/workflow-runs")
    assert resp.status_code == 200
    items = resp.json()
    target = next(item for item in items if item["id"] == run.id)
    assert target["lifecycle_status"] == schemas.WorkflowRunStatus.COMPLETED.value


@pytest.mark.asyncio
async def test_cleanup_with_null_external_id_marks_cleaned(session: AsyncSession):
    run = await _make_workflow_and_run(
        session,
        policy=schemas.CleanupPolicy.NEVER,
        lifecycle=schemas.WorkflowRunStatus.ERROR,
        external_id=None,
    )
    await crud.claim_workflow_run_for_cleanup(
        session,
        run_id=run.id,
        allowed_from=[schemas.CleanupStatus.NOT_REQUIRED],
    )

    await service._run_cleanup(run.id)

    refreshed = await _wait_for_cleanup(session, run.id, schemas.CleanupStatus.CLEANED)
    assert refreshed.cleaned_at is not None
