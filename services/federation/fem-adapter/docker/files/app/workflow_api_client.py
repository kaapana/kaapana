import json
import logging
from typing import Any, Optional
from urllib.parse import quote

import httpx

from config import settings

logger = logging.getLogger("fem-adapter")

TERMINAL_STATUSES = {"Completed", "Error", "Canceled"}


def _project_cookie() -> dict[str, str]:
    """
    workflow-api's POST /v1/workflow-runs reads the acting project from a
    "Project" cookie holding URL-encoded JSON with an "id" key, rather than
    from the request body. This builds that cookie for our fixed sandbox
    project.
    """
    return {"Project": quote(json.dumps({"id": settings.PROJECT_ID}))}


async def get_workflow_by_title(
    client: httpx.AsyncClient, title: str
) -> Optional[dict[str, Any]]:
    response = await client.get(
        f"{settings.WORKFLOW_API_BASE_URL}/workflows", params={"title": title}
    )
    response.raise_for_status()
    workflows = response.json()
    return workflows[0] if workflows else None


async def create_workflow(
    client: httpx.AsyncClient, title: str, definition: str
) -> dict[str, Any]:
    response = await client.post(
        f"{settings.WORKFLOW_API_BASE_URL}/workflows",
        json={
            "title": title,
            "workflow_engine": settings.WORKFLOW_ENGINE,
            "definition": definition,
        },
    )
    if response.status_code == 409:
        # Lost a race with another submit_run for the same task_id; the
        # workflow now exists, so reuse it instead of failing.
        existing = await get_workflow_by_title(client, title)
        assert existing is not None
        return existing
    response.raise_for_status()
    return response.json()


async def get_or_create_workflow(
    client: httpx.AsyncClient, task_id: str, command: str
) -> dict[str, Any]:
    """
    Kaapana Workflows are reused across submit_run calls for the same
    FEM task_id, keyed by a deterministic title.
    """
    title = f"fem-task-{task_id}"
    workflow = await get_workflow_by_title(client, title)
    if workflow is not None:
        return workflow
    return await create_workflow(client, title, definition=command)


async def create_workflow_run(
    client: httpx.AsyncClient, workflow: dict[str, Any]
) -> dict[str, Any]:
    response = await client.post(
        f"{settings.WORKFLOW_API_BASE_URL}/workflow-runs",
        json={
            "workflow": {
                "id": workflow["id"],
                "title": workflow["title"],
                "increment": workflow["increment"],
            }
        },
        cookies=_project_cookie(),
    )
    response.raise_for_status()
    return response.json()


async def get_workflow_run(client: httpx.AsyncClient, workflow_run_id: int) -> dict[str, Any]:
    response = await client.get(
        f"{settings.WORKFLOW_API_BASE_URL}/workflow-runs/{workflow_run_id}"
    )
    response.raise_for_status()
    return response.json()


async def cancel_workflow_run(client: httpx.AsyncClient, workflow_run_id: int) -> dict[str, Any]:
    response = await client.put(
        f"{settings.WORKFLOW_API_BASE_URL}/workflow-runs/{workflow_run_id}/cancel"
    )
    response.raise_for_status()
    return response.json()


async def force_dummy_status(
    client: httpx.AsyncClient, external_id: str, status: str
) -> None:
    """
    Sandbox-only: nudges workflow-api's DummyAdapter to a terminal status via
    its test-only router (ENABLE_TEST_ADAPTER=true). See
    Settings.DUMMY_ENGINE_AUTOCOMPLETE for why this exists.
    """
    response = await client.post(
        f"{settings.WORKFLOW_API_BASE_URL}/adapter-test/set-status/{external_id}",
        json={"status": status},
    )
    response.raise_for_status()
