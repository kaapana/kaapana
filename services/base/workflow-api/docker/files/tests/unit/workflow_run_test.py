"""
Unit tests for Workflow Run API.

Tests are organized by route/endpoint with clear markers:
- POST /v1/workflow-runs
- GET /v1/workflow-runs
- GET /v1/workflow-runs/{workflow_run_id}
- PUT /v1/workflow-runs/{workflow_run_id}/cancel
- PUT /v1/workflow-runs/{workflow_run_id}/retry
- GET /v1/workflow-runs/{workflow_run_id}/task-runs
- GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}
- GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs
"""

import sys
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

# Add current directory to path to import test_data
sys.path.insert(0, str(Path(__file__).parent))

from app import models, schemas  # noqa: E402
from test_data import LABEL_ENVIRONMENT_PROD, LABEL_TEAM, PARAM_LIST_ORGAN  # noqa: E402

# ============================================================
# POST /v1/workflow-runs - Create Workflow Run Tests
# ============================================================


@pytest.mark.POST
@pytest.mark.asyncio
async def test_create_workflow_run_basic(session: AsyncSession, client: AsyncClient):
    """Test creating a basic workflow run"""
    # Create a workflow first
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    # Create workflow run
    payload = {
        "workflow": {"title": "test-workflow", "version": 1},
        "workflow_parameters": [],
        "labels": [],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert data["id"] is not None
    assert data["workflow"]["title"] == "test-workflow"
    assert data["workflow"]["version"] == 1
    assert data["lifecycle_status"] == "Created"
    assert "Location" in response.headers
    assert response.headers["Location"] == f"/v1/workflow-runs/{data['id']}"


@pytest.mark.asyncio
async def test_create_workflow_run_with_labels(
    session: AsyncSession, client: AsyncClient
):
    """Test creating a workflow run with labels"""
    # Create a workflow
    workflow = models.Workflow(
        title="workflow-with-labels",
        version=1,
        definition="test_def",
        workflow_engine="dummy",
    )
    session.add(workflow)
    await session.commit()

    # Create workflow run with labels
    payload = {
        "workflow": {"title": "workflow-with-labels", "version": 1},
        "workflow_parameters": [],
        "labels": [LABEL_ENVIRONMENT_PROD, LABEL_TEAM],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()

    assert response.status_code == 201
    assert len(data["labels"]) == 2
    assert any(
        label["key"] == "environment" and label["value"] == "production"
        for label in data["labels"]
    )


@pytest.mark.asyncio
async def test_create_workflow_run_with_parameters(
    session: AsyncSession, client: AsyncClient
):
    """Test creating a workflow run with workflow parameters"""
    # Create a workflow
    workflow = models.Workflow(
        title="workflow-with-params",
        version=1,
        definition="test_def",
        workflow_engine="dummy",
    )
    session.add(workflow)
    await session.commit()

    # Create workflow run with parameters
    payload = {
        "workflow": {"title": "workflow-with-params", "version": 1},
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
    """Test creating a workflow run for non-existent workflow"""
    payload = {
        "workflow": {"title": "non-existent", "version": 1},
        "workflow_parameters": [],
        "labels": [],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    assert response.status_code == 404


# ============================================================
# GET /v1/workflow-runs - List Workflow Runs Tests
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_runs_empty(client: AsyncClient):
    """Test getting workflow runs when none exist"""
    response = await client.get("/v1/workflow-runs")
    data = response.json()

    assert response.status_code == 200
    assert data == []


@pytest.mark.asyncio
async def test_get_workflow_runs(session: AsyncSession, client: AsyncClient):
    """Test getting all workflow runs"""
    # Create workflow
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    # Create multiple workflow runs
    for i in range(3):
        workflow_run = models.WorkflowRun(workflow_id=workflow.id)
        session.add(workflow_run)
    await session.commit()

    response = await client.get("/v1/workflow-runs")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 3


@pytest.mark.asyncio
async def test_get_workflow_runs_filter_by_title(
    session: AsyncSession, client: AsyncClient
):
    """Test filtering workflow runs by workflow title"""
    # Create workflows
    workflow1 = models.Workflow(
        title="workflow-1", version=1, definition="test_def", workflow_engine="dummy"
    )
    workflow2 = models.Workflow(
        title="workflow-2", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow1)
    session.add(workflow2)
    await session.commit()
    await session.refresh(workflow1)
    await session.refresh(workflow2)

    # Create runs for both workflows
    run1 = models.WorkflowRun(workflow_id=workflow1.id)
    run2 = models.WorkflowRun(workflow_id=workflow2.id)
    session.add(run1)
    session.add(run2)
    await session.commit()

    # Filter by workflow-1
    response = await client.get("/v1/workflow-runs?workflow_title=workflow-1")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["workflow"]["title"] == "workflow-1"


@pytest.mark.asyncio
async def test_get_workflow_runs_filter_by_title_and_version(
    session: AsyncSession, client: AsyncClient
):
    """Test filtering workflow runs by workflow title and version"""
    # Create multiple versions
    workflow_v1 = models.Workflow(
        title="workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    workflow_v2 = models.Workflow(
        title="workflow", version=2, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow_v1)
    session.add(workflow_v2)
    await session.commit()
    await session.refresh(workflow_v1)
    await session.refresh(workflow_v2)

    # Create runs for both versions
    run_v1 = models.WorkflowRun(workflow_id=workflow_v1.id)
    run_v2 = models.WorkflowRun(workflow_id=workflow_v2.id)
    session.add(run_v1)
    session.add(run_v2)
    await session.commit()

    # Filter by title and version
    response = await client.get(
        "/v1/workflow-runs?workflow_title=workflow&workflow_version=2"
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["workflow"]["version"] == 2


# ============================================================
# GET /v1/workflow-runs/{workflow_run_id} - Get Workflow Run Tests
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_run_by_id(session: AsyncSession, client: AsyncClient):
    """Test getting a workflow run by ID"""
    # Create workflow and run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.get(f"/v1/workflow-runs/{workflow_run.id}")
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == workflow_run.id
    assert data["workflow"]["title"] == "test-workflow"


@pytest.mark.asyncio
async def test_get_workflow_run_by_id_not_found(client: AsyncClient):
    """Test getting non-existent workflow run"""
    response = await client.get("/v1/workflow-runs/99999")
    assert response.status_code == 404


# ============================================================
# PUT /v1/workflow-runs/{workflow_run_id}/cancel - Cancel Workflow Run Tests
# ============================================================


@pytest.mark.asyncio
async def test_cancel_workflow_run(session: AsyncSession, client: AsyncClient):
    """Test canceling a workflow run"""
    # Create workflow and run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.RUNNING,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/cancel")
    data = response.json()

    assert response.status_code == 200
    assert data["lifecycle_status"] == "Canceled"


@pytest.mark.asyncio
async def test_cancel_workflow_run_not_found(client: AsyncClient):
    """Test canceling non-existent workflow run"""
    response = await client.put("/v1/workflow-runs/99999/cancel")
    assert response.status_code == 404


# ============================================================
# PUT /v1/workflow-runs/{workflow_run_id}/retry - Retry Workflow Run Tests
# ============================================================


@pytest.mark.asyncio
async def test_retry_workflow_run(session: AsyncSession, client: AsyncClient):
    """Test retrying a failed workflow run"""
    # Create workflow and run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.ERROR,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/retry")
    data = response.json()

    assert response.status_code == 200
    # After retry, a new run is created
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_retry_workflow_run_not_found(client: AsyncClient):
    """Test retrying non-existent workflow run"""
    response = await client.put("/v1/workflow-runs/99999/retry")
    assert response.status_code == 404


# ============================================================
# GET /v1/workflow-runs/{workflow_run_id}/task-runs - Get Task Runs Tests
# ============================================================


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs(session: AsyncSession, client: AsyncClient):
    """Test getting task runs for a workflow run"""
    # Create workflow with tasks
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # Create workflow run in COMPLETED state (terminal state)
    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="test-external-id",
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    # Create task run with external_id
    task_run = models.TaskRun(
        task_id=task.id,
        workflow_run_id=workflow_run.id,
        lifecycle_status=schemas.TaskRunStatus.COMPLETED,
        external_id="task-external-id",
    )
    session.add(task_run)
    await session.commit()

    response = await client.get(f"/v1/workflow-runs/{workflow_run.id}/task-runs")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs_filter_by_title(
    session: AsyncSession, client: AsyncClient
):
    """Test filtering task runs by task title"""
    # Create workflow with multiple tasks
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task1 = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    task2 = models.Task(workflow_id=workflow.id, title="task2", type="DummyOperator")
    session.add(task1)
    session.add(task2)
    await session.commit()
    await session.refresh(task1)
    await session.refresh(task2)

    # Create workflow run in COMPLETED state (terminal state)
    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="test-external-id",
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    task_run1 = models.TaskRun(
        task_id=task1.id,
        workflow_run_id=workflow_run.id,
        external_id="task1-external-id",
    )
    task_run2 = models.TaskRun(
        task_id=task2.id,
        workflow_run_id=workflow_run.id,
        external_id="task2-external-id",
    )
    session.add(task_run1)
    session.add(task_run2)
    await session.commit()

    response = await client.get(
        f"/v1/workflow-runs/{workflow_run.id}/task-runs?task_title=task1"
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs_not_found(client: AsyncClient):
    """Test getting task runs for non-existent workflow run"""
    response = await client.get("/v1/workflow-runs/99999/task-runs")
    assert response.status_code == 404


# ============================================================
# GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id} - Get Task Run Tests
# ============================================================


@pytest.mark.asyncio
async def test_get_task_run(session: AsyncSession, client: AsyncClient):
    """Test getting a specific task run"""
    # Create workflow, task, run, and task run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    task_run = models.TaskRun(
        task_id=task.id,
        workflow_run_id=workflow_run.id,
        external_id="task-external-id",
    )
    session.add(task_run)
    await session.commit()
    await session.refresh(task_run)

    response = await client.get(
        f"/v1/workflow-runs/{workflow_run.id}/task-runs/{task_run.id}"
    )
    data = response.json()

    assert response.status_code == 200
    assert data["id"] == task_run.id
    assert data["task_title"] == "task1"


@pytest.mark.asyncio
async def test_get_task_run_not_found(session: AsyncSession, client: AsyncClient):
    """Test getting non-existent task run"""
    # Create workflow and run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.get(f"/v1/workflow-runs/{workflow_run.id}/task-runs/99999")
    assert response.status_code == 404


# ============================================================
# GET /v1/workflow-runs/{workflow_run_id}/task-runs/{task_run_id}/logs - Get Task Run Logs Tests
# ============================================================


@pytest.mark.asyncio
async def test_get_task_run_logs_not_found(session: AsyncSession, client: AsyncClient):
    """Test getting logs for non-existent task run"""
    # Create workflow and run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.get(
        f"/v1/workflow-runs/{workflow_run.id}/task-runs/99999/logs"
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run_logs(session: AsyncSession, client: AsyncClient):
    """Test getting logs for a task run"""
    # Create workflow, task, run, and task run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    task_run = models.TaskRun(
        task_id=task.id,
        workflow_run_id=workflow_run.id,
        external_id="task-external-id",
    )
    session.add(task_run)
    await session.commit()
    await session.refresh(task_run)

    response = await client.get(
        f"/v1/workflow-runs/{workflow_run.id}/task-runs/{task_run.id}/logs"
    )

    # Should return 200 with logs (may be empty string)
    assert response.status_code == 200
    assert isinstance(response.text, str)


@pytest.mark.asyncio
async def test_get_task_run_workflow_run_not_found(client: AsyncClient):
    """Test getting task run when workflow run doesn't exist"""
    response = await client.get("/v1/workflow-runs/99999/task-runs/1")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_task_run_logs_workflow_run_not_found(client: AsyncClient):
    """Test getting logs when workflow run doesn't exist"""
    response = await client.get("/v1/workflow-runs/99999/task-runs/1/logs")
    assert response.status_code == 404


# ============================================================
# Additional Edge Case Tests
# ============================================================


@pytest.mark.asyncio
async def test_create_workflow_run_increments_correctly(
    session: AsyncSession, client: AsyncClient
):
    """Test that multiple runs for same workflow are created correctly"""
    # Create workflow
    workflow = models.Workflow(
        title="multi-run-workflow",
        version=1,
        definition="test_def",
        workflow_engine="dummy",
    )
    session.add(workflow)
    await session.commit()

    payload = {
        "workflow": {"title": "multi-run-workflow", "version": 1},
        "workflow_parameters": [],
        "labels": [],
    }

    # Create 3 runs
    run_ids = []
    for _ in range(3):
        response = await client.post("/v1/workflow-runs", json=payload)
        assert response.status_code == 201
        data = response.json()
        run_ids.append(data["id"])

    # Verify all have unique IDs
    assert len(set(run_ids)) == 3


@pytest.mark.asyncio
async def test_cancel_already_completed_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    """Test canceling a workflow run that's already completed - status should remain completed"""
    # Create workflow and completed run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/cancel")
    data = response.json()
    
    # Should return 200 and status should remain completed
    assert response.status_code == 200
    assert data["lifecycle_status"] == "Completed"


@pytest.mark.asyncio
async def test_cancel_already_canceled_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    """Test canceling a workflow run that's already canceled - idempotent no-op"""
    # Create workflow and canceled run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.CANCELED,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/cancel")
    data = response.json()

    # Should return 200 and status should remain canceled (idempotent)
    assert response.status_code == 200
    assert data["lifecycle_status"] == "Canceled"


@pytest.mark.asyncio
async def test_cancel_error_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    """Test canceling a workflow run that's in error state - status should remain error"""
    # Create workflow and error run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.ERROR,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/cancel")
    data = response.json()

    # Should return 200 and status should remain error (terminal state immutability)
    assert response.status_code == 200
    assert data["lifecycle_status"] == "Error"


@pytest.mark.asyncio
async def test_retry_running_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    """Test retrying a workflow run that's still running"""
    # Create workflow and running run
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.RUNNING,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    response = await client.put(f"/v1/workflow-runs/{workflow_run.id}/retry")
    
    # Should fail or handle appropriately
    assert response.status_code in [200, 400, 409]


@pytest.mark.asyncio
async def test_workflow_run_with_multiple_labels(
    session: AsyncSession, client: AsyncClient
):
    """Test creating workflow run with multiple labels"""
    # Create workflow
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()

    payload = {
        "workflow": {"title": "test-workflow", "version": 1},
        "workflow_parameters": [],
        "labels": [
            {"key": "env", "value": "prod"},
            {"key": "team", "value": "ml"},
        ],
    }

    response = await client.post("/v1/workflow-runs", json=payload)
    data = response.json()
    
    assert response.status_code == 201
    assert len(data["labels"]) == 2


@pytest.mark.asyncio
async def test_get_workflow_runs_multiple_filters(
    session: AsyncSession, client: AsyncClient
):
    """Test combining multiple filters when getting workflow runs"""
    # Create workflows
    workflow1_v1 = models.Workflow(
        title="workflow-1", version=1, definition="test_def", workflow_engine="dummy"
    )
    workflow1_v2 = models.Workflow(
        title="workflow-1", version=2, definition="test_def", workflow_engine="dummy"
    )
    workflow2_v1 = models.Workflow(
        title="workflow-2", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add_all([workflow1_v1, workflow1_v2, workflow2_v1])
    await session.commit()
    await session.refresh(workflow1_v1)
    await session.refresh(workflow1_v2)
    await session.refresh(workflow2_v1)

    # Create runs
    run1 = models.WorkflowRun(workflow_id=workflow1_v1.id)
    run2 = models.WorkflowRun(workflow_id=workflow1_v2.id)
    run3 = models.WorkflowRun(workflow_id=workflow2_v1.id)
    session.add_all([run1, run2, run3])
    await session.commit()

    # Filter by title and version
    response = await client.get(
        "/v1/workflow-runs?workflow_title=workflow-1&workflow_version=2"
    )
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["workflow"]["title"] == "workflow-1"
    assert data[0]["workflow"]["version"] == 2


@pytest.mark.asyncio
async def test_task_run_belongs_to_correct_workflow_run(
    session: AsyncSession, client: AsyncClient
):
    """Test that task runs are properly associated with their workflow run"""
    # Create workflow with task
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    # Create two workflow runs
    run1 = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="run1",
    )
    run2 = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
        external_id="run2",
    )
    session.add_all([run1, run2])
    await session.commit()
    await session.refresh(run1)
    await session.refresh(run2)

    # Create task runs for each workflow run
    task_run1 = models.TaskRun(
        task_id=task.id, workflow_run_id=run1.id, external_id="task-run1"
    )
    task_run2 = models.TaskRun(
        task_id=task.id, workflow_run_id=run2.id, external_id="task-run2"
    )
    session.add_all([task_run1, task_run2])
    await session.commit()

    # Get task runs for run1 only
    response = await client.get(f"/v1/workflow-runs/{run1.id}/task-runs")
    data = response.json()

    assert response.status_code == 200
    assert len(data) == 1
    assert data[0]["external_id"] == "task-run1"


@pytest.mark.asyncio
async def test_get_workflow_run_with_labels(
    session: AsyncSession, client: AsyncClient
):
    """Test getting workflow run that has labels"""
    # Create workflow
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    # Create workflow run
    workflow_run = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
    )
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    # Add labels using the many-to-many relationship
    label1 = models.Label(key="env", value="prod")
    label2 = models.Label(key="team", value="ml")
    session.add_all([label1, label2])
    await session.commit()
    
    # Associate labels with workflow run
    workflow_run.labels = [label1, label2]
    await session.commit()
    await session.refresh(workflow_run)

    # Get the workflow run
    response = await client.get(f"/v1/workflow-runs/{workflow_run.id}")
    data = response.json()

    assert response.status_code == 200
    assert len(data["labels"]) == 2
    label_dict = {label["key"]: label["value"] for label in data["labels"]}
    assert label_dict["env"] == "prod"
    assert label_dict["team"] == "ml"


@pytest.mark.asyncio
async def test_get_workflow_runs_with_status_filter(
    session: AsyncSession, client: AsyncClient
):
    """Test filtering workflow runs by lifecycle status"""
    # Create workflow
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    # Create runs with different statuses
    run_completed = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.COMPLETED,
    )
    run_running = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.RUNNING,
    )
    run_error = models.WorkflowRun(
        workflow_id=workflow.id,
        lifecycle_status=schemas.WorkflowRunStatus.ERROR,
    )
    session.add_all([run_completed, run_running, run_error])
    await session.commit()

    # Filter by completed status
    response = await client.get("/v1/workflow-runs?lifecycle_status=COMPLETED")
    data = response.json()

    assert response.status_code == 200
    assert len(data) >= 1
    # All returned runs should have Completed status
    assert all(run["lifecycle_status"] == "Completed" for run in data)


@pytest.mark.asyncio
async def test_task_run_lifecycle_status(
    session: AsyncSession, client: AsyncClient
):
    """Test that task runs have proper lifecycle status"""
    # Create workflow with task
    workflow = models.Workflow(
        title="test-workflow", version=1, definition="test_def", workflow_engine="dummy"
    )
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)

    task = models.Task(workflow_id=workflow.id, title="task1", type="DummyOperator")
    session.add(task)
    await session.commit()
    await session.refresh(task)

    workflow_run = models.WorkflowRun(workflow_id=workflow.id)
    session.add(workflow_run)
    await session.commit()
    await session.refresh(workflow_run)

    # Create task run with specific status
    task_run = models.TaskRun(
        task_id=task.id,
        workflow_run_id=workflow_run.id,
        lifecycle_status=schemas.TaskRunStatus.ERROR,
        external_id="task-external-id",
    )
    session.add(task_run)
    await session.commit()
    await session.refresh(task_run)

    response = await client.get(
        f"/v1/workflow-runs/{workflow_run.id}/task-runs/{task_run.id}"
    )
    data = response.json()

    assert response.status_code == 200
    assert data["lifecycle_status"] == "Error"
