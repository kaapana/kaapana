import httpx
from dotenv import load_dotenv
import os
from app import schemas

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
    return await httpx.AsyncClient(base_url=API_BASE_URL, verify=False).post(
        "/workflows",
        json=workflow_create.model_dump(),
    )


async def get_workflow_by_title(title) -> httpx.Response:
    return await httpx.AsyncClient(verify=False).get(
        f"{API_BASE_URL}/workflows/{title}",
    )


async def get_workflow_by_title_and_version(title, version) -> httpx.Response:
    return await httpx.AsyncClient(verify=False).get(
        f"{API_BASE_URL}/workflows/{title}/{version}",
    )


async def delete_workflow(headers, title, version) -> httpx.Response:
    return await httpx.AsyncClient(verify=False).delete(
        f"{API_BASE_URL}/workflows/{title}/{version}",
    )
