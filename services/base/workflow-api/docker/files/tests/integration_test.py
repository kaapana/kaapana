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


# @pytest.mark.asyncio
# async def test_get_runs_for_workflow(auth_headers_and_cookies):
#     """
#     Tests retrieving runs for a specific workflow (by latest and by version).
#     Covers:
#     - GET /workflows/{identifier}/runs
#     - GET /workflows/{identifier}/{version}/runs
#     """
#     headers, cookies = auth_headers_and_cookies

#     workflow = schemas.WorkflowCreate(
#         identifier="collect-metadata",
#         definition="A test workflow for getting runs",
#     )

#     # 1. Create a workflow
#     workflow_response = await create_or_get_workflow(
#         headers, cookies, workflow.model_dump()
#     )
#     identifier = workflow_response["identifier"]
#     version = workflow_response["version"]

#     async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
#         # 2. Create a run for this workflow to ensure the list isn't empty
#         run_payload = {
#             "config": {
#                 "data_form": {
#                     "identifiers": [
#                         "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
#                     ],
#                     "dataset_name": "phantom",
#                 },
#                 "workflow_form": {
#                     "single_execution": False,
#                 },
#             },
#             "labels": {},
#         }
#         run_response = await client.post(
#             f"{BASE_URL}/workflow-api/v1/workflows/{identifier}/versions/{version}/runs",
#             headers=headers,
#             cookies=cookies,
#             json=run_payload,
#         )
#         assert run_response.status_code == 200
#         run_id = run_response.json()["id"]

#         # 3. Get runs for the workflow's latest version
#         latest_runs_response = await client.get(
#             f"/workflow-api/v1/workflows/{identifier}/runs",
#             headers=headers,
#             cookies=cookies,
#         )
#         assert latest_runs_response.status_code == 200
#         latest_runs_data = latest_runs_response.json()
#         assert isinstance(latest_runs_data, list)
#         assert any(run["id"] == run_id for run in latest_runs_data)

#         # 4. Get runs for the specific version
#         version_runs_response = await client.get(
#             f"/workflow-api/v1/workflows/{identifier}/versions/{version}/runs",
#             headers=headers,
#             cookies=cookies,
#         )
#         assert version_runs_response.status_code == 200
#         version_runs_data = version_runs_response.json()
#         assert isinstance(version_runs_data, list)
#         assert any(run["id"] == run_id for run in version_runs_data)

#     # Cleanup
#     await delete_workflow(headers, cookies, identifier)


# @pytest.mark.asyncio
# async def test_get_task_run_details_and_logs(auth_headers_and_cookies):
#     """
#     Tests retrieving a specific task run and its logs.
#     This requires creating a workflow with a task, running it, and waiting
#     for the task to start.
#     Covers:
#     - GET /runs/{run_id}/tasks/{task_id}/task-run
#     - GET /runs/{run_id}/tasks/{task_id}/task-run/logs
#     """
#     headers, cookies = auth_headers_and_cookies
#     # Use a workflow that is known to run and complete successfully
#     workflow = schemas.WorkflowCreate(
#         identifier="collect-metadata",
#         definition="A test workflow",
#     )

#     # 1. Ensure workflow exists
#     workflow_response = await create_or_get_workflow(
#         headers, cookies, workflow.model_dump()
#     )
#     identifier = workflow.identifier
#     version = workflow_response["version"]

#     # This ID must match an actual task_id within the 'collect-metadata' workflow definition
#     task_id_in_definition = "collect-metadata"

#     async with httpx.AsyncClient(
#         base_url=BASE_URL, verify=False, timeout=120
#     ) as client:
#         # 2. Create a workflow run
#         run_payload = {
#             "config": {
#                 "data_form": {
#                     "identifiers": [
#                         "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
#                     ],
#                     "dataset_name": "phantom",
#                 },
#                 "workflow_form": {"single_execution": False},
#             },
#             "labels": {},
#         }
#         run_response = await client.post(
#             f"/workflow-api/v1/workflows/{identifier}/versions/{version}/runs",
#             headers=headers,
#             cookies=cookies,
#             json=run_payload,
#         )
#         assert run_response.status_code == 200
#         run_id = run_response.json()["id"]
# Not implemeted logs yet
# # 3. Poll until the run is active or complete to ensure task-runs are created
# task_run_found = False
# for _ in range(20): # Poll for up to 60 seconds
#     status_response = await client.get(
#         f"/workflow-api/v1/runs/{run_id}/task-runs", headers=headers, cookies=cookies
#     )
#     assert status_response.status_code == 200
#     data = status_response.json()
#     run_status = data["lifecycle_status"]
#     task_id = data["task_id"]

#     if run_status in ["Running", "Completed", "Failed"]:
#         # 4. Get the specific task-run once the parent run is active
#         task_run_response = await client.get(
#             f"/workflow-api/v1/runs/{run_id}/tasks/{task_id}/task-run",
#             headers=headers, cookies=cookies
#         )
#         if task_run_response.status_code == 200:
#             task_run_data = task_run_response.json()
#             assert task_run_data["task_id"] == task_id_in_definition
#             assert task_run_data["run_id"] == run_id

#             # 5. Get the logs for that task-run
#             logs_response = await client.get(
#                 f"/workflow-api/v1/runs/{run_id}/tasks/{task_id}/task-run/logs",
#                 headers=headers, cookies=cookies
#             )
#             assert logs_response.status_code == 200
#             # Logs should be returned as text content
#             assert isinstance(logs_response.text, str)

#             task_run_found = True
#             break

#     await asyncio.sleep(3)

# assert (
#     task_run_found
# ), f"Could not find or retrieve task-run for task '{task_id_in_definition}' in run '{run_id}'"


# @pytest.mark.asyncio
# async def test_workflow_ui_schema(auth_headers_and_cookies):
#     """
#     Tests creating and retrieving UI schemas for workflows.
#     Covers:
#     - POST /workflows/{identifier}/versions/{version}/ui-schema
#     - GET /workflows/{identifier}/versions/{version}/ui-schema
#     - POST /workflows/{identifier}/versions/latest/ui-schema
#     - GET /workflows/{identifier}/ui-schema
#     """
#     headers, cookies = auth_headers_and_cookies
#     workflow = schemas.WorkflowCreate(
#         identifier="collect-metadata",
#         definition="A test workflow",
#     )

#     # 1. Create a workflow to work with
#     workflow_response = await create_or_get_workflow(
#         headers, cookies, workflow.model_dump()
#     )
#     identifier = workflow_response["identifier"]
#     version = workflow_response["version"]

#     ui_schema_payload = {
#         "schema_definition": {
#             "data_form": {
#                 "identifiers": [
#                     "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
#                 ],
#                 "dataset_name": "phantom",
#             },
#             "workflow_form": {"single_execution": False},
#         }
#     }

#     async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
#         # 2. POST to create a UI schema for a specific version
#         post_version_url = (
#             f"/workflow-api/v1/workflows/{identifier}/versions/{version}/ui-schema"
#         )
#         post_response = await client.post(
#             post_version_url, headers=headers, cookies=cookies, json=ui_schema_payload
#         )
#         assert post_response.status_code == 200
#         assert (
#             post_response.json()["schema_definition"]
#             == ui_schema_payload["schema_definition"]
#         )

#         # 3. GET the UI schema for that specific version to verify
#         get_version_url = (
#             f"/workflow-api/v1/workflows/{identifier}/versions/{version}/ui-schema"
#         )
#         get_version_response = await client.get(
#             get_version_url, headers=headers, cookies=cookies
#         )
#         assert get_version_response.status_code == 200
#         assert (
#             post_response.json()["schema_definition"]
#             == ui_schema_payload["schema_definition"]
#         )

#     # Cleanup
#     await delete_workflow(headers, cookies, identifier)
