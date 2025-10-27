from datetime import datetime

import httpx
import pytest
from app import schemas

from . import common

API_BASE_URL = "http://localhost:8080/v1"


@pytest.mark.asyncio
async def test_connection():
    async with httpx.AsyncClient(base_url="http://localhost:8080/") as client:
        response = await client.get("/docs#/")
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_create_and_get_workflows():
    """
    Ensure workflows can be created and then listed
    """
    title1 = f"wf-{int(datetime.now().timestamp())}-1"
    title2 = f"wf-{int(datetime.now().timestamp())}-2"

    resp1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title1,
            definition="create-get-wf1",
            workflow_engine="dummy",
            labels=[schemas.Label(key="created_from_test", value="true")],
        )
    )
    assert resp1.status_code == 201
    resp2 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title2,
            definition="create-get-wf2",
            workflow_engine="dummy",
            labels=[schemas.Label(key="created_from_test", value="true")],
        )
    )
    assert resp2.status_code == 201

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.get(
            "/workflows",
            params={"skip": 0, "limit": 50, "order_by": "created_at", "order": "desc"},
        )
        assert response.status_code == 200
        workflows = [schemas.Workflow(**wf) for wf in response.json()]
        print(f"{workflows=}")
        titles = [wf.title for wf in workflows]
        assert title1 in titles
        assert title2 in titles


@pytest.mark.asyncio
async def test_get_workflows_by_title():
    """
    Ensure GET /workflows/{title} returns latest or all versions
    """
    title = f"wf-title-{datetime.now().timestamp()}"

    resp1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title, definition="def-v1", workflow_engine="dummy"
        )
    )
    assert resp1.status_code == 201
    resp2 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title, definition="def-v2", workflow_engine="dummy"
        )
    )
    assert resp2.status_code == 201

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        # latest=True should return only newest version
        response = await client.get(f"/workflows/{title}", params={"latest": True})
        assert response.status_code == 200
        workflows = [schemas.Workflow(**wf) for wf in response.json()]
        assert len(workflows) == 1
        assert workflows[0].definition == "def-v2"

        # latest=False should return both versions
        response = await client.get(f"/workflows/{title}", params={"latest": False})
        assert response.status_code == 200
        workflows = [schemas.Workflow(**wf) for wf in response.json()]
        assert len(workflows) == 2


@pytest.mark.asyncio
async def test_get_workflow_by_title_version():
    """
    Ensure workflows can be fetched by title+version.
    """
    title = f"wf-byver-test-{datetime.now().timestamp()}"
    resp1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title, definition="test-by-version", workflow_engine="Airflow"
        )
    )
    assert resp1.status_code == 201
    wf1 = schemas.Workflow(**resp1.json())

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp = await client.get(f"/workflows/{wf1.title}/{wf1.version}")
        assert resp.status_code == 200
        wf = schemas.Workflow(**resp.json())
        assert wf.id == wf1.id
        assert wf.definition == wf1.definition


@pytest.mark.asyncio
async def test_delete_workflow():
    """
    Ensure workflows can be deleted and no longer retrievable.
    """
    title = f"wf-del-{datetime.now().timestamp()}"
    resp = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title, definition="test-to-be-deleted", workflow_engine="Airflow"
        )
    )
    assert resp.status_code == 201
    wf = schemas.Workflow(**resp.json())

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        del_resp = await client.delete(f"/workflows/{wf.title}/{wf.version}")
        assert del_resp.status_code == 204

        get_resp = await client.get(f"/workflows/{wf.title}/{wf.version}")
        assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_get_workflow_tasks():
    title = f"wf-gettasks-test-{datetime.now().timestamp()}"
    resp1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title, definition="test-get-tests", workflow_engine="dummy"
        )
    )
    assert resp1.status_code == 201
    wf1 = schemas.Workflow(**resp1.json())

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        resp1 = await client.get(f"/workflows/{wf1.title}/{wf1.version}")
        assert resp1.status_code == 200
        wf = schemas.Workflow(**resp1.json())
        assert wf.id == wf1.id
        assert wf.definition == wf1.definition

        # get all tasks of the workflow
        resp2 = await client.get(f"/workflows/{wf1.title}/{wf1.version}/tasks")
        assert resp2.status_code == 200
        tasks = resp2.json()
        assert len(tasks) == 2
        task2_id = None  # get task2 id for downstream check later on
        for task in tasks:
            t = schemas.Task(**task)
            assert t.title in ["dummy-task-1", "dummy-task-2"]
            if t.title == "dummy-task-2":
                task2_id = t.id
        assert task2_id is not None

        # get specific task by title
        resp3 = await client.get(
            f"/workflows/{wf1.title}/{wf1.version}/tasks/dummy-task-1"
        )
        assert resp3.status_code == 200
        task = schemas.Task(**resp3.json())
        assert task.title == "dummy-task-1"
        assert task.display_name == "Dummy Task 1"
        # check for downstream task
        assert (
            len(task.downstream_task_ids) == 1
            and task.downstream_task_ids[0] == task2_id
        )


@pytest.mark.asyncio
async def test_get_workflows_perf_under_200ms():
    """
    Measure GET /workflows with limit=100 and ensure response time is under 200ms
    """
    async with httpx.AsyncClient(base_url=API_BASE_URL, timeout=5.0) as client:
        import time

        start = time.perf_counter()
        resp = await client.get("/workflows", params={"skip": 0, "limit": 100})
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert resp.status_code == 200
        assert (
            elapsed_ms < 200
        ), f"GET /workflows took {elapsed_ms:.1f}ms, expected <200ms"
