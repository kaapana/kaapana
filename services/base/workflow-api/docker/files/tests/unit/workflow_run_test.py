"""
Unit tests for Workflow Run API.

Routes covered:
- POST /v1/workflow-runs
- GET /v1/workflow-runs (optional ?workflow_id=, ?workflow_increment=)
- GET /v1/workflow-runs/{workflow_run_id}
- PUT /v1/workflow-runs/{workflow_run_id}/cancel
- PUT /v1/workflow-runs/{workflow_run_id}/retry
- GET /v1/workflow-runs/{workflow_run_id}/task-runs
- GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}
- GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs
- GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/raw-logs
"""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

sys.path.insert(0, str(Path(__file__).parent))

from app import models, schemas  # noqa: E402
from test_data import LABEL_ENVIRONMENT_PROD, LABEL_TEAM, PARAM_LIST_ORGAN  # noqa: E402


import uuid as _uuid


async def _first_revision_id(client: AsyncClient, wf: dict) -> _uuid.UUID:
    r = await client.get(f"/v1/workflows/{wf['id']}/revisions")
    revs = r.json()
    return _uuid.UUID(min(revs, key=lambda x: x["increment"])["id"])


# ============================================================
# POST /v1/workflow-runs
# ============================================================


@pytest.mark.POST
@pytest.mark.asyncio
async def test_create_workflow_run_basic(session: AsyncSession, client: AsyncClient):
    """Creating a basic workflow run returns 201 with id, lifecycle CREATED and Location header."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()

    payload = {
        "workflow": {"id": str(wf["id"]), "title": wf["title"], "increment": 1},
        "workflow_parameters": [],
        "labels": [],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()

    assert response.status_code == 201, data
    assert data["id"] is not None
    assert data["workflow"]["id"] == str(wf["id"])
    assert data["workflow"]["increment"] == 1
    assert data["lifecycle_status"] == "Created"
    assert response.headers["Location"] == f"/v1/workflow-runs/{data['id']}"


@pytest.mark.asyncio
async def test_create_workflow_run_with_labels(
    session: AsyncSession, client: AsyncClient
):
    """Creating a workflow run with labels persists them and surfaces them in the response."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "workflow-with-labels",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()

    payload = {
        "workflow": {"id": str(wf["id"]), "title": wf["title"], "increment": 1},
        "workflow_parameters": [],
        "labels": [LABEL_ENVIRONMENT_PROD, LABEL_TEAM],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()

    assert response.status_code == 201
    # The run is auto-pinned to its project via an immutable label, on top of
    # the two user labels.
    user_labels = [
        l for l in data["labels"] if l["key"] != "kaapana.immutable.project_id"
    ]
    assert len(user_labels) == 2
    assert any(l["key"] == "kaapana.immutable.project_id" for l in data["labels"])


@pytest.mark.asyncio
async def test_create_workflow_run_with_parameters(
    session: AsyncSession, client: AsyncClient
):
    """Workflow run created with workflow_parameters echoes them back unchanged."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "workflow-with-params",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()

    payload = {
        "workflow": {"id": str(wf["id"]), "title": wf["title"], "increment": 1},
        "workflow_parameters": [PARAM_LIST_ORGAN],
        "labels": [],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert len(data["workflow_parameters"]) == 1
    assert data["workflow_parameters"][0]["task_title"] == "segmentation"


@pytest.mark.asyncio
async def test_create_workflow_run_workflow_not_found(client: AsyncClient):
    """POST /workflow-runs with a non-existent workflow id returns 404."""
    payload = {
        "workflow": {
            "id": "00000000-0000-0000-0000-000000000000",
            "title": "does-not-exist",
            "increment": 1,
        },
        "workflow_parameters": [],
        "labels": [],
    }
    response = await client.post("/v1/workflow-runs", json=payload)
    assert response.status_code == 404


# ============================================================
# GET /v1/workflow-runs
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_runs_empty(client: AsyncClient):
    """GET /workflow-runs returns 200 with an empty list when no runs exist."""
    response = await client.get("/v1/workflow-runs")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_get_workflow_runs(session: AsyncSession, client: AsyncClient):
    """GET /workflow-runs lists all runs across workflows."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    for _ in range(3):
        session.add(models.WorkflowRun(workflow_revision_id=rev_id))
    await session.commit()

    response = await client.get("/v1/workflow-runs")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_workflow_runs_filter_by_workflow_id(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflow-runs?workflow_id=... filters runs by source workflow id."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "workflow-1",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf1 = _r.json()
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "workflow-2",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf2 = _r.json()
    session.add(
        models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf1))
    )
    session.add(
        models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf2))
    )
    await session.commit()

    response = await client.get(f"/v1/workflow-runs?workflow_id={wf1['id']}")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["workflow"]["id"] == str(wf1["id"])


@pytest.mark.asyncio
async def test_get_workflow_runs_filter_by_workflow_id_and_increment(
    session: AsyncSession, client: AsyncClient
):
    """Combining workflow_id + workflow_increment filters scopes runs to a specific revision."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "multi-rev-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    _r = await client.patch(f"/v1/workflows/{wf['id']}", json={"definition": "v2"})

    assert _r.status_code == 200, _r.text

    # PATCH returns the Workflow schema with the latest increment merged in.
    # Look up the revision id for increment=2 separately.
    _r = await client.get(f"/v1/workflows/{wf['id']}/revisions/2")
    rev2_id = _uuid.UUID(_r.json()["id"])
    session.add(
        models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf))
    )
    session.add(models.WorkflowRun(workflow_revision_id=rev2_id))
    await session.commit()

    response = await client.get(
        f"/v1/workflow-runs?workflow_id={wf['id']}&workflow_increment=2"
    )
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["workflow"]["increment"] == 2


# ============================================================
# GET /v1/workflow-runs/{id}
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_run_by_id(session: AsyncSession, client: AsyncClient):
    """GET /workflow-runs/{id} returns the requested run."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf))
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.get(f"/v1/workflow-runs/{run.id}")
    data = response.json()
    assert response.status_code == 200
    assert data["id"] == run.id
    assert data["workflow"]["id"] == str(wf["id"])


@pytest.mark.asyncio
async def test_get_workflow_run_by_id_not_found(client: AsyncClient):
    """GET /workflow-runs/{id} returns 404 for an unknown id."""
    response = await client.get("/v1/workflow-runs/99999")
    assert response.status_code == 404


# ============================================================
# Cancel / Retry
# ============================================================


@pytest.mark.asyncio
async def test_cancel_workflow_run(session: AsyncSession, client: AsyncClient):
    """PUT /workflow-runs/{id}/cancel transitions the run to CANCELED."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(
        workflow_revision_id=await _first_revision_id(client, wf),
        external_id="test-external-id",
        lifecycle_status=schemas.WorkflowRunStatus.RUNNING,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.put(f"/v1/workflow-runs/{run.id}/cancel")
    data = response.json()
    assert response.status_code == 200
    assert data["lifecycle_status"] == "Canceled"


@pytest.mark.asyncio
async def test_cancel_workflow_run_not_found(client: AsyncClient):
    """Canceling a non-existent workflow run returns 404."""
    response = await client.put("/v1/workflow-runs/99999/cancel")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_retry_workflow_run(session: AsyncSession, client: AsyncClient):
    """Retrying a failed workflow run goes through the engine adapter and the
    response carries the run id back."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "retry-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    workflow_run = models.WorkflowRun(
        workflow_revision_id=rev_id,
        lifecycle_status=schemas.WorkflowRunStatus.ERROR,
        external_id="retry-external-id",
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/retry")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == workflow_run.id


@pytest.mark.asyncio
async def test_retry_workflow_run_not_found(client: AsyncClient):
    """Retrying a non-existent workflow run returns 404."""
    response = await client.put("/v1/workflow-runs/99999/retry")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_workflow_run_increments_correctly(
    session: AsyncSession, client: AsyncClient
):
    """Multiple POSTs for the same workflow revision produce distinct run ids."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "multi-run-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()

    payload = {
        "workflow": {"id": str(wf["id"]), "title": wf["title"], "increment": 1},
        "workflow_parameters": [],
        "labels": [],
    }

    run_ids = []
    for _ in range(3):
        response = await client.post("/v1/workflow-runs", json=payload)
        assert response.status_code == 201
        run_ids.append(response.json()["id"])

    # all three runs are distinct rows
    assert len(set(run_ids)) == 3


# ============================================================
# Task runs
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs(session: AsyncSession, client: AsyncClient):
    """GET /workflow-runs/{id}/task-runs lists the task runs for a workflow run."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    run = models.WorkflowRun(
        workflow_revision_id=rev_id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="test-external-id",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    task_run = models.TaskRun(
        task_id=task.id,
        workflow_run_id=run.id,
        lifecycle_status=schemas.TaskRunStatus.COMPLETED,
        external_id="task-external-id",
    )
    session.add(task_run)
    await session.commit()

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs_filter_by_title(
    session: AsyncSession, client: AsyncClient
):
    """GET /workflow-runs/{id}/task-runs?task_title=... scopes to one task."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    t1 = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    t2 = models.Task(workflow_revision_id=rev_id, title="task2", type="Op")
    session.add_all([t1, t2])
    await session.commit()
    await session.refresh(t1)
    await session.refresh(t2)

    run = models.WorkflowRun(
        workflow_revision_id=rev_id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="test-external-id",
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    tr1 = models.TaskRun(task_id=t1.id, workflow_run_id=run.id, external_id="tr1-ext")
    tr2 = models.TaskRun(task_id=t2.id, workflow_run_id=run.id, external_id="tr2-ext")
    session.add_all([tr1, tr2])
    await session.commit()

    response = await client.get(
        f"/v1/workflow-runs/{run.id}/task-runs?task_title=task1"
    )
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs_not_found(client: AsyncClient):
    """Task-runs lookup for a non-existent workflow run returns 404."""
    response = await client.get("/v1/workflow-runs/99999/task-runs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run(session: AsyncSession, client: AsyncClient):
    """GET /workflow-runs/{id}/task-runs/{task_run_id} returns the specific task run."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    run = models.WorkflowRun(workflow_revision_id=rev_id)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    tr = models.TaskRun(task_id=task.id, workflow_run_id=run.id, external_id="task-ext")
    session.add(tr)
    await session.commit()
    await session.refresh(tr)

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs/{tr.id}")
    data = response.json()
    assert response.status_code == 200
    assert data["id"] == tr.id
    assert data["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_task_run_not_found(session: AsyncSession, client: AsyncClient):
    """GET /task-runs/{id} returns 404 for an unknown task run."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf))
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs/99999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run_logs_not_found(session: AsyncSession, client: AsyncClient):
    """Logs lookup for a non-existent task run returns 404."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(workflow_revision_id=await _first_revision_id(client, wf))
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs/99999/logs")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run_logs(session: AsyncSession, client: AsyncClient):
    """GET /task-runs/{id}/logs returns parsed LogLine objects (time, severity, message)."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    run = models.WorkflowRun(workflow_revision_id=rev_id)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    tr = models.TaskRun(task_id=task.id, workflow_run_id=run.id, external_id="task-ext")
    session.add(tr)
    await session.commit()
    await session.refresh(tr)

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs/{tr.id}/logs")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    for line in data:
        assert "time" in line
        assert "severity" in line
        assert "message" in line


@pytest.mark.asyncio
async def test_get_task_run_raw_logs(session: AsyncSession, client: AsyncClient):
    """GET /task-runs/{id}/raw-logs returns the raw engine log string."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "test-workflow-raw",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    run = models.WorkflowRun(workflow_revision_id=rev_id)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    tr = models.TaskRun(task_id=task.id, workflow_run_id=run.id, external_id="task-ext")
    session.add(tr)
    await session.commit()
    await session.refresh(tr)

    response = await client.get(
        f"/v1/workflow-runs/{run.id}/task-runs/{tr.id}/raw-logs"
    )
    assert response.status_code == 200
    assert isinstance(response.text, str)


@pytest.mark.asyncio
async def test_get_task_run_workflow_run_not_found(client: AsyncClient):
    """Task-run lookup where the parent workflow run doesn't exist returns 404."""
    response = await client.get("/v1/workflow-runs/99999/task-runs/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run_logs_workflow_run_not_found(client: AsyncClient):
    """Task-run logs lookup where the parent workflow run doesn't exist returns 404."""
    response = await client.get("/v1/workflow-runs/99999/task-runs/1/logs")
    assert response.status_code == 404


# ============================================================
# Cancel/Retry parametrized
# ============================================================


@pytest.mark.parametrize(
    "initial_status, expected_status_after_retry, expect_external_id",
    [
        (schemas.WorkflowRunStatus.RUNNING, schemas.WorkflowRunStatus.PENDING, True),
        (schemas.WorkflowRunStatus.PENDING, schemas.WorkflowRunStatus.PENDING, True),
        (schemas.WorkflowRunStatus.SCHEDULED, schemas.WorkflowRunStatus.PENDING, True),
        (schemas.WorkflowRunStatus.CANCELED, schemas.WorkflowRunStatus.CANCELED, True),
        (
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.COMPLETED,
            True,
        ),
        (schemas.WorkflowRunStatus.ERROR, schemas.WorkflowRunStatus.ERROR, True),
        (schemas.WorkflowRunStatus.CREATED, schemas.WorkflowRunStatus.CREATED, False),
    ],
)
@pytest.mark.asyncio
async def test_retry_workflow_run_from_any_status(
    session: AsyncSession,
    client: AsyncClient,
    initial_status: schemas.WorkflowRunStatus,
    expected_status_after_retry: schemas.WorkflowRunStatus,
    expect_external_id: bool,
):
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "retry-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(
        workflow_revision_id=await _first_revision_id(client, wf),
        external_id="test-external-id" if expect_external_id else None,
        lifecycle_status=initial_status,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.put(f"/v1/workflow-runs/{run.id}/retry")
    data = response.json()
    assert response.status_code == 200
    assert data["lifecycle_status"] == expected_status_after_retry.value

    if expect_external_id:
        assert data["external_id"] is not None
    else:
        assert data["external_id"] is None


@pytest.mark.parametrize(
    "initial_status, expected_status_after_cancel, expect_external_id",
    [
        (schemas.WorkflowRunStatus.RUNNING, schemas.WorkflowRunStatus.CANCELED, True),
        (schemas.WorkflowRunStatus.PENDING, schemas.WorkflowRunStatus.CANCELED, True),
        (schemas.WorkflowRunStatus.SCHEDULED, schemas.WorkflowRunStatus.CANCELED, True),
        (schemas.WorkflowRunStatus.CANCELED, schemas.WorkflowRunStatus.CANCELED, True),
        (
            schemas.WorkflowRunStatus.COMPLETED,
            schemas.WorkflowRunStatus.COMPLETED,
            True,
        ),
        (schemas.WorkflowRunStatus.ERROR, schemas.WorkflowRunStatus.ERROR, True),
        (schemas.WorkflowRunStatus.CREATED, schemas.WorkflowRunStatus.CREATED, False),
    ],
)
@pytest.mark.asyncio
async def test_cancel_workflow_run_from_any_status(
    session: AsyncSession,
    client: AsyncClient,
    initial_status: schemas.WorkflowRunStatus,
    expected_status_after_cancel: schemas.WorkflowRunStatus,
    expect_external_id: bool,
):
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "cancel-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(
        workflow_revision_id=await _first_revision_id(client, wf),
        external_id="test-external-id" if expect_external_id else None,
        lifecycle_status=initial_status,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    response = await client.put(f"/v1/workflow-runs/{run.id}/cancel")
    data = response.json()
    assert response.status_code == 200
    assert data["lifecycle_status"] == expected_status_after_cancel.value
    if expect_external_id:
        assert data["external_id"] is not None
    else:
        assert data["external_id"] is None


# ============================================================
# Misc
# ============================================================


@pytest.mark.asyncio
async def test_workflow_run_with_multiple_labels(
    session: AsyncSession, client: AsyncClient
):
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "multi-label-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    payload = {
        "workflow": {"id": str(wf["id"]), "title": wf["title"], "increment": 1},
        "workflow_parameters": [],
        "labels": [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "ml"},
        ],
    }
    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()
    assert response.status_code == 201
    user_labels = [
        l for l in data["labels"] if l["key"] != "kaapana.immutable.project_id"
    ]
    assert len(user_labels) == 2
    assert any(l["key"] == "kaapana.immutable.project_id" for l in data["labels"])


@pytest.mark.asyncio
async def test_task_run_belongs_to_correct_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "affinity-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    r1 = models.WorkflowRun(
        workflow_revision_id=rev_id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="run1",
    )
    r2 = models.WorkflowRun(
        workflow_revision_id=rev_id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="run2",
    )
    session.add_all([r1, r2])
    await session.commit()
    await session.refresh(r1)
    await session.refresh(r2)

    tr1 = models.TaskRun(task_id=task.id, workflow_run_id=r1.id, external_id="tr1")
    tr2 = models.TaskRun(task_id=task.id, workflow_run_id=r2.id, external_id="tr2")
    session.add_all([tr1, tr2])
    await session.commit()

    response = await client.get(f"/v1/workflow-runs/{r1.id}/task-runs")
    data = response.json()
    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["external_id"] == "tr1"
    assert data[0]["workflow_run_id"] == r1.id


@pytest.mark.asyncio
async def test_get_workflow_run_with_labels(session: AsyncSession, client: AsyncClient):
    """A workflow run created with labels returns them on subsequent GET."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "labeled-run-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    run = models.WorkflowRun(
        workflow_revision_id=await _first_revision_id(client, wf),
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
    )
    session.add(run)
    await session.commit()
    await session.refresh(run)

    l1 = models.Label(key="env", value="prod")
    l2 = models.Label(key="team", value="ml")
    session.add_all([l1, l2])
    await session.commit()

    run.labels = [l1, l2]
    await session.commit()
    await session.refresh(run)

    response = await client.get(f"/v1/workflow-runs/{run.id}")
    data = response.json()
    assert response.status_code == 200
    assert len(data["labels"]) == 2
    label_dict = {l["key"]: l["value"] for l in data["labels"]}
    assert label_dict["env"] == "prod"
    assert label_dict["team"] == "ml"


@pytest.mark.asyncio
async def test_get_workflow_runs_with_status_filter(
    session: AsyncSession, client: AsyncClient
):
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "status-filter-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    for status in [
        schemas.WorkflowRunStatus.COMPLETED,
        schemas.WorkflowRunStatus.RUNNING,
        schemas.WorkflowRunStatus.ERROR,
    ]:
        session.add(
            models.WorkflowRun(
                workflow_revision_id=rev_id,
                lifecycle_status=status,
                external_id=f"ext-{status.value}",
            )
        )
    await session.commit()

    response = await client.get("/v1/workflow-runs?lifecycle_status=COMPLETED")
    data = response.json()
    assert response.status_code == 200
    assert all(run["lifecycle_status"] == "Completed" for run in data)


@pytest.mark.asyncio
async def test_task_run_lifecycle_status(session: AsyncSession, client: AsyncClient):
    """Task runs persisted in the DB return their lifecycle status verbatim."""
    _r = await client.post(
        "/v1/workflows",
        json={
            "title": "task-lifecycle-workflow",
            "definition": "test_def",
            "workflow_engine": "dummy",
            "workflow_parameters": [],
            "labels": [],
        },
    )

    assert _r.status_code == 201, _r.text

    wf = _r.json()
    rev_id = await _first_revision_id(client, wf)
    task = models.Task(workflow_revision_id=rev_id, title="task1", type="Op")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    run = models.WorkflowRun(workflow_revision_id=rev_id)
    session.add(run)
    await session.commit()
    await session.refresh(run)

    tr = models.TaskRun(
        task_id=task.id,
        workflow_run_id=run.id,
        lifecycle_status=schemas.TaskRunStatus.ERROR,
        external_id="task-ext",
    )
    session.add(tr)
    await session.commit()
    await session.refresh(tr)

    response = await client.get(f"/v1/workflow-runs/{run.id}/task-runs/{tr.id}")
    data = response.json()
    assert response.status_code == 200
    assert data["lifecycle_status"] == "Error"
