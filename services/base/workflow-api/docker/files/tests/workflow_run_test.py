import pytest
import httpx
from datetime import datetime
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
    Ensure GET /workflow-runs/{id} returns the coorect run
    """
    title = f"wfrun-byid-{datetime.utcnow().timestamp()}"
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
    title = f"wfrun-cancel-{datetime.utcnow().timestamp()}"
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
        assert canceled.lifecycle_status == schemas.LifecycleStatus.CANCELED
