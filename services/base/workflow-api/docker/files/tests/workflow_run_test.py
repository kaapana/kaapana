from datetime import datetime

import httpx
import pytest
from app import schemas

from . import common

API_BASE_URL = "http://localhost:8080/v1"


@pytest.mark.asyncio
async def test_create_and_get_workflow_run():
    """
    Ensure workflow runs can be created and then listed
    """
    # create a new workflow
    title = f"wfrun-test-createget-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="Airflow")
    )
    assert wf_resp.status_code == 201
    wf = schemas.Workflow(**wf_resp.json())

    # create a new workflow run for that workflow
    new_run = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=wf.title, version=wf.version),
        labels=[schemas.Label(key="test", value="true")],
    )
    wf_run_resp = await common.create_workflow_run(new_run)

    assert wf_run_resp.status_code == 201
    run = schemas.WorkflowRun(**wf_run_resp.json())
    assert run.workflow.title == wf.title
    assert run.workflow.version == wf.version

    # fetch all runs
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        print(f"type of title {wf.title=} is {type(wf.title)}")
        runs = await client.get("/workflow-runs", params={"workflow_title": wf.title})
        assert runs.status_code == 200
        runs = [schemas.WorkflowRun(**r) for r in runs.json()]
        assert any(r.id == run.id for r in runs)


@pytest.mark.asyncio
async def test_get_workflow_run_by_id():
    """
    Ensure GET /workflow-runs/{id} returns the correct run
    """
    title = f"wfrun-byid-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="Airflow")
    )
    wf = schemas.Workflow(**wf_resp.json())

    new_run = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=wf.title, version=wf.version),
        labels=[schemas.Label(key="test", value="true")],
    )
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        create_resp = await client.post("/workflow-runs", json=new_run.model_dump())
        assert create_resp.status_code == 201
        run = schemas.WorkflowRun(**create_resp.json())

        get_resp = await client.get(f"/workflow-runs/{run.id}")
        assert get_resp.status_code == 200
        fetched = schemas.WorkflowRun(**get_resp.json())
        assert fetched.id == run.id


@pytest.mark.asyncio
async def test_cancel_workflow_run():
    """
    Ensure PUT /workflow-runs/{id}/cancel cancels the run
    """
    title = f"wfrun-cancel-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="Airflow")
    )
    wf = schemas.Workflow(**wf_resp.json())

    new_run = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=wf.title, version=wf.version),
        labels=[schemas.Label(key="test", value="true")],
    )
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        create_resp = await client.post("/workflow-runs", json=new_run.model_dump())
        run = schemas.WorkflowRun(**create_resp.json())

        cancel_resp = await client.put(f"/workflow-runs/{run.id}/cancel")
        assert cancel_resp.status_code == 200
        canceled = schemas.WorkflowRun(**cancel_resp.json())
        assert canceled.lifecycle_status == schemas.WorkflowRunStatus.CANCELED


@pytest.mark.asyncio
async def test_get_workflow_run_task_runs():
    """
    Ensure GET /workflow-runs/{workflow_run_id}/task-runs returns task runs
    """
    title = f"wfrun-taskruns-{datetime.now().timestamp()}"
    wf_resp = await common.create_workflow(
        schemas.WorkflowCreate(title=title, definition="def", workflow_engine="dummy")
    )
    wf = schemas.Workflow(**wf_resp.json())

    new_run = schemas.WorkflowRunCreate(
        workflow=schemas.WorkflowRef(title=wf.title, version=wf.version),
        labels=[schemas.Label(key="test", value="true")],
    )

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        # create and get the workflow run
        create_resp = await client.post("/workflow-runs", json=new_run.model_dump())
        assert create_resp.status_code == 201
        create_wf_run = schemas.WorkflowRun(**create_resp.json())

        get_resp = await client.get(f"/workflow-runs/{create_wf_run.id}")
        assert get_resp.status_code == 200
        wf_run = schemas.WorkflowRun(**get_resp.json())
        assert wf_run.id == create_wf_run.id

        # get task runs of the workflow run
        task_runs_resp = await client.get(f"/workflow-runs/{wf_run.id}/task-runs")
        assert task_runs_resp.status_code == 200
        task_runs = [schemas.TaskRun(**tr) for tr in task_runs_resp.json()]
        assert len(task_runs) > 0
        for tr in task_runs:
            assert tr.task_title in ["dummy-task-1", "dummy-task-2"]
            assert tr.lifecycle_status == schemas.TaskRunStatus.RUNNING


@pytest.mark.asyncio
async def test_get_workflow_runs_perf_under_200ms():
    """
    Measure GET /workflow-runs with limit=100 and ensure response time is under 200ms
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=5.0) as client:
        import time

        start = time.perf_counter()
        resp = await client.get("/workflow-runs", params={"skip": 0, "limit": 100})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert (
            elapsed_ms < 200
        ), f"GET /workflow-runs took {elapsed_ms:.1f}ms, expected <200ms"
