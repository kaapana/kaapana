import pytest
import httpx
from app import schemas

from .common import (
    get_auth_and_project,
    HOST,
    CLIENT_SECRET,
    BASE_URL,
    create_workflow,
    delete_workflow,
    create_or_get_workflow,
)


@pytest.fixture(scope="session")
def auth_headers_and_cookies():
    return get_auth_and_project(host=HOST, client_secret=CLIENT_SECRET)


@pytest.mark.asyncio
async def test_get_workflows(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.get(
            "/workflow-api/v1/workflows", headers=headers, cookies=cookies
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_and_delete_workflow(auth_headers_and_cookies):

    workflow = schemas.WorkflowCreate(
        identifier="example-workflow",
        definition="A test workflow",
    )
    headers, cookies = auth_headers_and_cookies
    data = await create_workflow(headers, cookies, payload=workflow.model_dump())
    assert data["identifier"] == workflow.identifier
    # assert data["version"] == 1
    assert data["definition"] == workflow.definition
    assert data["config_definition"] == workflow.config_definition
    data = await delete_workflow(headers, cookies, workflow.identifier)


@pytest.mark.asyncio
async def test_get_workflow_by_identifier_and_version(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="example-workflow",
        definition="A test workflow",
    )
    data = await create_or_get_workflow(headers, cookies, workflow.model_dump())

    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await httpx.AsyncClient(verify=False).get(
            f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/versions/{data["version"]}",
            headers=headers,
            cookies=cookies,
        )
        assert response.status_code == 200
        assert response.json()["identifier"] == data["identifier"]
        assert response.json()["version"] == data["version"]
        assert response.json()["definition"] == data["definition"]
        assert response.json()["config_definition"] == data["config_definition"]
        data = await delete_workflow(headers, cookies, workflow.identifier)


@pytest.mark.asyncio
async def test_get_latest_version_workflow(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="example-workflow",
        definition="A test workflow",
    )
    data = await create_or_get_workflow(headers, cookies, payload=workflow.model_dump())

    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await httpx.AsyncClient(verify=False).get(
            f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/latest",
            headers=headers,
            cookies=cookies,
        )
        assert response.status_code == 200
        assert response.status_code == 200
        assert response.json()["identifier"] == data["identifier"]
        assert response.json()["version"] == data["version"]
    data = await delete_workflow(headers, cookies, workflow.identifier)


@pytest.mark.asyncio
async def test_get_workflow_versions(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="example-workflow",
        definition="A test workflow",
    )
    data = await create_or_get_workflow(headers, cookies, payload=workflow.model_dump())
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflows/{workflow.identifier}/versions",
        headers=headers,
        cookies=cookies,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    data = await delete_workflow(headers, cookies, workflow.identifier)


@pytest.mark.asyncio
async def test_get_workflow_tasks(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="example-workflow",
        definition="A test workflow",
    )
    data = await create_or_get_workflow(headers, cookies, payload=workflow.model_dump())

    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/versions",
        headers=headers,
        cookies=cookies,
    )
    version = response.json()[0]["version"]  # Get the latest version
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/versions/{version}/tasks",
        headers=headers,
        cookies=cookies,
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_workflow_run(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="test-workflow",
        definition="A test workflow",
        labels={"kaapana.builtin.workflow_engine": "dummy"},
    )
    # Ensure workflow exists (same as your existing code)
    data = await create_or_get_workflow(headers, cookies, payload=workflow.model_dump())

    workflow_run = schemas.WorkflowRunCreateForWorkflow(config={}, labels={})
    async with httpx.AsyncClient(verify=False) as client:
        # Create workflow run
        run_response = await client.post(
            f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/versions/{data["version"]}/runs",
            headers=headers,
            cookies=cookies,
            json=workflow_run.model_dump(),
        )
        run_response.raise_for_status()
        assert run_response.status_code == 200
        run_data = run_response.json()
        run_id = run_data["id"]
        status_response = await client.get(
            f"{BASE_URL}/workflow-api/v1/runs/{run_id}",
            headers=headers,
            cookies=cookies,
        )

        assert status_response.status_code == 200
        run_status = status_response.json()["lifecycle_status"]
        assert run_status == "Pending"


@pytest.mark.asyncio
async def test_get_all_runs(auth_headers_and_cookies):
    """
    Tests retrieving the list of all workflow runs.
    Covers: GET /runs
    """
    headers, cookies = auth_headers_and_cookies
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.get(
            "/workflow-api/v1/runs", headers=headers, cookies=cookies
        )
        assert response.status_code == 200
        # The response should be a list, even if it's empty
        assert isinstance(response.json(), list)
