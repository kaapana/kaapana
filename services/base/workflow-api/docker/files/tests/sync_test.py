import pytest
from datetime import datetime
import httpx

from app import schemas
from . import common

API_BASE_URL = "http://localhost:8080/v1"


@pytest.mark.asyncio
async def test_sync_full_lifecycle():
    """
    Tests the full lifecycle transition using the DummyAdapter test API endpoints.
    """

    # create a new workflow
    title = f"sync-lifecycle-test-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="dummy")
    )
    assert wf_resp.status_code == 201
    wf = schemas.Workflow(**wf_resp.json())

    # create a new workflow run for that workflow
    new_run = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=wf.title, version=wf.version)
    )
    wf_run_resp = await common.create_workflow_run(new_run)
    assert wf_run_resp.status_code == 201

    run_initial = schemas.WorkflowRun(**wf_run_resp.json())
    run_id = run_initial.id
    assert run_initial.lifecycle_status == schemas.WorkflowRunStatus.CREATED

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:

        # get workflow run to fetch external_id
        await client.get(f"/workflow-runs/{run_id}")
        run_fetched = schemas.WorkflowRun(
            **(await client.get(f"/workflow-runs/{run_id}")).json()
        )
        external_id = run_fetched.external_id
        assert external_id is not None

        # set the worflow run to Running
        await client.post(
            f"/test-adapter/set-status/{external_id}",
            json={"status": schemas.WorkflowRunStatus.RUNNING},
        )

        sync_resp = await client.post("/workflow-runs/sync")
        assert sync_resp.status_code == 204

        run_synced_1 = schemas.WorkflowRun(
            **(await client.get(f"/workflow-runs/{run_id}")).json()
        )
        assert run_synced_1.lifecycle_status == schemas.WorkflowRunStatus.RUNNING

        # set the worflow run to Completed
        await client.post(
            f"/adapter-test/set-status/{external_id}",
            json={"status": schemas.WorkflowRunStatus.COMPLETED},
        )

        sync_resp = await client.post("/workflow-runs/sync")
        assert sync_resp.status_code == 204

        run_synced_2 = schemas.WorkflowRun(
            **(await client.get(f"/workflow-runs/{run_id}")).json()
        )
        assert run_synced_2.lifecycle_status == schemas.WorkflowRunStatus.COMPLETED


@pytest.mark.asyncio
async def test_sync_updates_tasks():
    """
    Ensures syncing fetches task runs from the DummyAdapter
    and persists them in DB.
    """

    title = f"sync-tasks-update-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="dummy")
    )
    wf = schemas.Workflow(**wf_resp.json())

    wf_run_resp = await common.create_workflow_run(
        schemas.WorkflowRunCreate(
            workflow=schemas.WorkflowRef(title=wf.title, version=wf.version)
        )
    )
    run_id = wf_run_resp.json()["id"]

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        await client.post("/workflow-runs/sync")

        resp = await client.get(f"/workflow-runs/{run_id}/task-runs")
        assert resp.status_code == 200
        task_runs = resp.json()

        assert len(task_runs) == 2
        assert task_runs[0]["lifecycle_status"] == schemas.WorkflowRunStatus.RUNNING
