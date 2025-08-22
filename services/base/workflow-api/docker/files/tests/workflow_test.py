import pytest
from app import schemas
from . import common
import httpx

API_BASE_URL = "http://localhost:8080/v1"


@pytest.mark.asyncio
async def test_connection():
    async with httpx.AsyncClient(base_url="http://localhost:8080/") as client:
        response = await client.get("/docs#/")
        response.raise_for_status()


@pytest.mark.asyncio
async def test_get_workflows():
    """
    POST /v1/workflows
    GET /v1/workflows
    """
    response1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title="test1",
            definition="test1",
        )
    )
    assert response1.raise_for_status() and response1.status_code == 201
    response2 = await common.create_workflow(
        schemas.WorkflowCreate(
            title="test2",
            definition="test2",
        )
    )
    assert response2.raise_for_status() and response2.status_code == 201
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        params = {"skip": 0, "limit": 2}
        response = await client.get("/workflows", params=params)
        response.raise_for_status()
        workflows = [schemas.Workflow(**wf) for wf in response.json()]
        assert len(workflows) == 2


@pytest.mark.asyncio
async def test_get_workflow_by_title():
    """
    POST /v1/workflows
    GET /v1/workflows/{title}
    """
    title = "test1"

    response1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title,
            definition="First one",
        )
    )
    assert response1.raise_for_status() and response1.status_code == 201
    response2 = await common.create_workflow(
        schemas.WorkflowCreate(
            title=title,
            definition="Second one",
        )
    )
    assert response2.raise_for_status() and response2.status_code == 201
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        params = {"skip": 0, "limit": 2}
        response = await client.get(f"/workflows/{title}", params=params)
        response.raise_for_status()
        workflows = [schemas.Workflow(**wf) for wf in response.json()]
        assert len(workflows) == 2

        for wf in workflows:
            assert wf.title == title


@pytest.mark.asyncio
async def test_get_workflow_by_title_version():
    """
    POST /v1/workflows
    GET /v1/workflows/{title}/{version}
    """
    response1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title="test1",
            definition="First one",
        )
    )
    assert response1.raise_for_status() and response1.status_code == 201
    response2 = await common.create_workflow(
        schemas.WorkflowCreate(
            title="test1",
            definition="First one",
        )
    )
    assert response2.raise_for_status() and response2.status_code == 201

    workflow1 = schemas.Workflow(**response1.json())
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.get(f"/workflows/{workflow1.title}/{workflow1.version}")
        response.raise_for_status()
        assert schemas.Workflow(**response.json()).id == workflow1.id


@pytest.mark.asyncio
async def test_delete():
    """
    POST /v1/workflows
    DELETE /v1/workflows/{title}/{version}
    """
    response1 = await common.create_workflow(
        schemas.WorkflowCreate(
            title="test1",
            definition="First one",
        )
    )
    assert response1.raise_for_status() and response1.status_code == 201

    workflow1 = schemas.Workflow(**response1.json())
    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        response = await client.delete(
            f"/workflows/{workflow1.title}/{workflow1.version}"
        )
        response.raise_for_status()
        response.status_code == 204
        get_response = await client.get(
            f"/workflows/{workflow1.title}/{workflow1.version}"
        )
        assert get_response.status_code == 404
