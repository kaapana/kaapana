import os
from typing import Optional

import httpx
from app import schemas
from dotenv import load_dotenv

load_dotenv()
# 🔐 Login credentials and Keycloak setup
USERNAME = os.getenv("USERNAME", "kaapana")
PASSWORD = os.getenv("PASSWORD", "admin")
PROTOCOL = os.getenv("PROTOCOL", "https")
HOST = os.getenv("HOST")
PORT = os.getenv("PORT", 443)
SSL_CHECK = False if os.getenv("SSL_CHECK", "False").lower == "false" else True
CLIENT_ID = os.getenv("CLIENT_ID", "kaapana")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

API_BASE_URL = "http://localhost:8080/v1"


async def create_workflow(workflow_create: schemas.WorkflowCreate) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.post(
            "/workflows",
            json=workflow_create.model_dump(),
            timeout=10.0,
        )


async def get_workflow_by_title(
    title: str, params: Optional[dict] = None
) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.get(f"/workflows/{title}", params=params)


async def get_all_workflows(params: Optional[dict] = None) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.get("/workflows", params=params)


async def get_workflow_by_title_and_version(
    title: str, version: int
) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.get(f"/workflows/{title}/{version}")


async def delete_workflow(title: str, version: int) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.delete(f"/workflows/{title}/{version}")


async def create_workflow_run(
    workflow_run_create: schemas.WorkflowRunCreate,
) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.post(
            "/workflow-runs",
            json=workflow_run_create.model_dump(),
        )


async def get_all_workflow_runs(params: Optional[dict] = None) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.get("/workflow-runs", params=params)


async def delete_workflow_run(workflow_run_id: int) -> httpx.Response:
    async with httpx.AsyncClient(base_url=API_BASE_URL, verify=False) as client:
        return await client.delete(f"/workflow-runs/{workflow_run_id}")
