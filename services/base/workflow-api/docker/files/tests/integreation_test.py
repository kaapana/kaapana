import pytest
import httpx
from typing import Dict
import requests
import json
import asyncio
# 🔐 Login credentials and Keycloak setup
USERNAME = "kaapana"#"your-user"
PASSWORD = "admin"  #"your-pass"
PROTOCOL = "https"
HOST = "your.host.local" # add here
PORT = 443  
SSL_CHECK = False
CLIENT_ID = "kaapana"
CLIENT_SECRET = "your-client-secret" # replace



BASE_URL = f"{PROTOCOL}://{HOST}:{PORT}"


def get_auth_and_project(host, client_secret):
    # Get access token
    payload = {
        "username": "kaapana",
        "password": "admin",
        "client_id": "kaapana",
        "client_secret": client_secret,
        "grant_type": "password",
    }
    token_url = f"https://{host}/auth/realms/kaapana/protocol/openid-connect/token"
    token_res = requests.post(token_url, verify=False, data=payload)
    token_res.raise_for_status()
    access_token = token_res.json()["access_token"]

    # Get admin project
    headers = {"Authorization": f"Bearer {access_token}"}
    project_url = f"https://{host}/aii/projects/admin"
    project_res = requests.get(project_url, verify=False, headers=headers)
    project_res.raise_for_status()
    project = project_res.json()

    # Compose headers and cookie
    project_header = {
        "id": project["id"],
        "external_id": project["external_id"],
        "name": project["name"],
        "description": project["description"],
    }
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Project": json.dumps(project_header),
    }
    cookies = {
        "Project": json.dumps({"name": project["name"], "id": project["id"]})
    }
    return headers, cookies


@pytest.fixture(scope="session")
def auth_headers_and_cookies():
    return get_auth_and_project(host=HOST, client_secret=CLIENT_SECRET)

@pytest.mark.asyncio
async def test_get_workflows(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.get("/workflow-api/v1/", headers=headers, cookies=cookies)
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_workflow(auth_headers_and_cookies):
    payload = {
        "identifier": "example-workflow",
        "definition": "A test workflow",
        "config_definition": {"key": "value"},
    }
    headers, cookies = auth_headers_and_cookies
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.post("/workflow-api/v1/", headers=headers, cookies=cookies, json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["identifier"] == "example-workflow"
        #assert data["version"] == 1
        assert data["definition"] == "A test workflow"
        assert data["config_definition"] == {"key": "value"}

@pytest.mark.asyncio
async def test_delete_workflow(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    # First recreate the workflow
    await httpx.AsyncClient(verify=False).post(
        f"{BASE_URL}/workflow-api/v1/",
        headers=headers,
        cookies=cookies,
        json={
            "identifier": "workflow-to-delete",
            "definition": "delete test",
            "config_definition": {}
        }
    )
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflow-to-delete/latest",
        headers=headers, cookies=cookies
    )
    assert response.status_code == 200
    version = response.json()["version"]
    response = await httpx.AsyncClient(verify=False).delete(
        f"{BASE_URL}/workflow-api/v1/workflow-to-delete/{version}",
        headers=headers,
        cookies=cookies
    )
    assert response.status_code == 204

@pytest.mark.asyncio
async def test_get_workflow_by_identifier_and_version(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    payload = {
        "identifier": "example-workflowxx",
        "definition": "A test workflow",
        "config_definition": {"key": "value"},
    }
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.post("/workflow-api/v1/", headers=headers, cookies=cookies, json=payload)
        assert response.status_code == 200
        data = response.json()

        response = await httpx.AsyncClient(verify=False).get(
            f"{BASE_URL}/workflow-api/v1/{data["identifier"]}/{data["version"]}",
            headers=headers, cookies=cookies
        )
        assert response.status_code == 200
        assert response.json()["identifier"] == data["identifier"]
        assert response.json()["version"] == data["version"]
        assert response.json()["definition"] == data["definition"]
        assert response.json()["config_definition"] == data["config_definition"]


        response = await httpx.AsyncClient(verify=False).delete(
            f"{BASE_URL}/workflow-api/v1/{data["identifier"]}/{data["version"]}",
            headers=headers,
            cookies=cookies
        )
        assert response.status_code == 204


@pytest.mark.asyncio
async def test_get_latest_version_workflow(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/latest",
        headers=headers, cookies=cookies
    )
    assert response.status_code == 200
    assert response.json()["identifier"] == "example-workflow"


@pytest.mark.asyncio
async def test_get_workflow_versions(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/versions",
        headers=headers, cookies=cookies
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)





@pytest.mark.asyncio
async def test_get_workflow_tasks(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/versions",
        headers=headers, cookies=cookies
    )
    version = response.json()[0]["version"]  # Get the latest version
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/{version}/tasks",
        headers=headers, cookies=cookies
    )
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_workflow_task(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/versions",
        headers=headers, cookies=cookies
    )
    version = response.json()[0]["version"]
    response = await httpx.AsyncClient(verify=False).post(
        f"{BASE_URL}/workflow-api/v1/example-workflow/{version}/tasks",
        headers=headers, cookies=cookies,
        json={"display_name": "test-task", 
        "type": "TotalSegmentatorOperator",
        "task_id": "test-task-id", 
        "input_tasks_ids": ["task1", "task2"],
        "output_tasks_ids": ["task3"]   
        }
    )
    assert response.status_code == 200
    assert response.json()["display_name"] == "test-task"


@pytest.mark.asyncio
async def test_get_task_by_id(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/example-workflow/versions",
        headers=headers, cookies=cookies
    )
    version = response.json()[0]["version"]

    
    # First, create task
    task_response = await httpx.AsyncClient(verify=False).post(
        f"{BASE_URL}/workflow-api/v1/example-workflow/{version}/tasks",
        headers=headers, cookies=cookies,
        json={"display_name": "create-test-task", 
        "type": "TotalSegmentatorOperator",
        "task_id": "create-test-task-id", 
        "input_tasks_ids": ["task1", "task2"],
        "output_tasks_ids": ["task3"]   
        }
    )
    task_id = task_response.json()["id"]
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/tasks/{task_id}",
        headers=headers, cookies=cookies
    )
    assert response.status_code == 200
    assert response.json()["id"] == task_id
    assert response.json()["display_name"] == "create-test-task"





@pytest.mark.asyncio
async def test_workflow_run_lifecycle(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies

    # Ensure workflow exists (same as your existing code)
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(f"{BASE_URL}/workflow-api/v1/collect-metadata/1", headers=headers, cookies=cookies)

        if response.status_code == 404:
            payload = {
                "identifier": "collect-metadata",
                "definition": "A test workflow",
                "config_definition": {"key": "value"},
            }
            response = await client.post(f"{BASE_URL}/workflow-api/v1/", headers=headers, cookies=cookies, json=payload)
        assert response.status_code == 200
        version = response.json()["version"]
        # Create workflow run
        run_response = await client.post(
            f"{BASE_URL}/workflow-api/v1/collect-metadata/{version}/runs",
            headers=headers, cookies=cookies,
            json={
                "config": {
                    "data_form": {
                        "identifiers": [
                            "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
                        ],
                        "dataset_name": "phantom"
                    },
                    "workflow_form": {
                        "single_execution": False,
                    }
                },
                "labels": {}
            }
        )
        assert run_response.status_code == 200
        run_data = run_response.json()
        run_id = run_data["id"]

        # Now poll the run status repeatedly to assert all states
        expected_states = ["Scheduled", "Running", "Completed"]
        observed_states = []

        max_attempts = 20
        for _ in range(max_attempts):
            status_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/collect-metadata/1/runs/{run_id}",
                headers=headers, cookies=cookies
            )

            assert status_response.status_code == 200
            run_status = status_response.json()["lifecycle_status"] 
            
            if run_status not in observed_states:
                observed_states.append(run_status)
            
            # If run reached a final state, break early
            if run_status == "Completed":
                break
            # also get tasks for the run
            tasks_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/runs/{run_id}/task-runs",
                headers=headers, cookies=cookies
            )
            # wait a bit before polling again
            await asyncio.sleep(3)

        # Assert that all expected states were observed in order
        # It's okay if intermediate states repeat, so check inclusion and order
        idx = 0
        for state in observed_states:
            if state == expected_states[idx]:
                idx += 1
                if idx == len(expected_states):
                    break

        assert idx == len(expected_states), f"States did not progress as expected. Observed states: {observed_states}"


@pytest.mark.asyncio
async def test_workflow_run_canceled(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies

    # Ensure workflow exists (same as your existing code)
    async with httpx.AsyncClient(verify=False) as client:
        response = await client.get(f"{BASE_URL}/workflow-api/v1/collect-metadata/1", headers=headers, cookies=cookies)
        if response.status_code == 404:
            payload = {
                "identifier": "collect-metadata",
                "definition": "A test workflow",
                "config_definition": {"key": "value"},
            }
            response = await client.post(f"{BASE_URL}/workflow-api/v1/", headers=headers, cookies=cookies, json=payload)
        assert response.status_code == 200
        version = response.json()["version"]
        # Create workflow run
        run_response = await client.post(
            f"{BASE_URL}/workflow-api/v1/collect-metadata/{version}/runs",
            headers=headers, cookies=cookies,
            json={
                "config": {
                    "data_form": {
                        "identifiers": [
                            "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
                        ],
                        "dataset_name": "phantom"
                    },
                    "workflow_form": {
                        "single_execution": False,
                    }
                },
                "labels": {}
            }
        )
        assert run_response.status_code == 200
        run_data = run_response.json()
        run_id = run_data["id"]

         # Now poll the run status repeatedly to assert all states
        expected_states = ["Scheduled", "Running", "Canceled"]
        observed_states = []

        max_attempts = 20
        for _ in range(max_attempts):
            status_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/collect-metadata/1/runs/{run_id}",
                headers=headers, cookies=cookies
            )

            assert status_response.status_code == 200
            run_status = status_response.json()["lifecycle_status"] 
            
            if run_status not in observed_states:
                observed_states.append(run_status)
            
            if run_status == "Running":
                # Cancel the run while it's running
                cancel_response = await client.put(
                    f"{BASE_URL}/workflow-api/v1/runs/{run_id}/cancel",
                    headers=headers, cookies=cookies
                )
                assert cancel_response.status_code == 200
            # If run reached a final state, break early
            if run_status == "Completed" or run_status == "Canceled":
                break
            # also get tasks for the run
            tasks_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/runs/{run_id}/task-runs",
                headers=headers, cookies=cookies
            )
            # wait a bit before polling again
            await asyncio.sleep(3)
        # Assert that all expected states were observed in order
        # It's okay if intermediate states repeat, so check inclusion and order
        idx = 0
        for state in observed_states:
            if state == expected_states[idx]:
                idx += 1
                if idx == len(expected_states):
                    break

        assert idx == len(expected_states), f"States did not progress as expected. Observed states: {observed_states}"

