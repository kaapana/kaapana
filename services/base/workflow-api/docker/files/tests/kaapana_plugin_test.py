import pytest
import httpx
import asyncio
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
async def test_workflow_run(auth_headers_and_cookies):
    headers, cookies = auth_headers_and_cookies
    workflow = schemas.WorkflowCreate(
        identifier="collect-metadata",
        definition="A test workflow",
        labels={"kaapana.builtin.workflow_engine": "kaapana-plugin"},
    )
    data = await create_or_get_workflow(headers, cookies, payload=workflow.model_dump())

    workflow_run = schemas.WorkflowRunCreateForWorkflow(
        config={
            "data_form": {
                "identifiers": [
                    "1.3.12.2.1107.5.1.4.73104.30000020081307523376400012735"
                ],
                "dataset_name": "phantom",
            },
            "project_form": {
                "id": "95c664fc-709d-493b-9a96-49f05712bc3b",
                "external_id": None,
                "name": "admin",
                "int_id": None,
                "description": "Initial admin project",
                "kubernetes_namespace": "project-admin",
                "s3_bucket": "project-admin",
                "opensearch_index": "project_admin",
            },
            "workflow_form": {
                "single_execution": False,
            },
        },
    )
    async with httpx.AsyncClient(verify=False) as client:
        # Create workflow run
        run_response = await client.post(
            f"{BASE_URL}/workflow-api/v1/workflows/{data["identifier"]}/versions/{data["version"]}/runs",
            headers=headers,
            cookies=cookies,
            json=workflow_run.model_dump(),
        )
        assert run_response.status_code == 200
        run_data = run_response.json()
        run_id = run_data["id"]

        # Now poll the run status repeatedly to assert all states
        expected_states = ["Scheduled", "Running", "Canceled"]
        observed_states = []

        max_attempts = 1
        for _ in range(max_attempts):
            status_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/runs/{run_id}",
                headers=headers,
                cookies=cookies,
            )

            assert status_response.status_code == 200
            run_status = status_response.json()["lifecycle_status"]

            if run_status not in observed_states:
                observed_states.append(run_status)

            # if run_status == "Running":
            #     # Cancel the run while it's running
            #     cancel_response = await client.put(
            #         f"{BASE_URL}/workflow-api/v1/runs/{run_id}/cancel",
            #         headers=headers,
            #         cookies=cookies,
            #     )
            #     assert cancel_response.status_code == 200
            # If run reached a final state, break early
            if run_status == "Completed" or run_status == "Canceled":
                break
            # also get tasks for the run
            tasks_response = await client.get(
                f"{BASE_URL}/workflow-api/v1/runs/{run_id}/task-runs",
                headers=headers,
                cookies=cookies,
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

        assert idx == len(
            expected_states
        ), f"States did not progress as expected. Observed states: {observed_states}"
