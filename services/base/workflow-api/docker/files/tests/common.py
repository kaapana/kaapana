import httpx
import requests
import json
from dotenv import load_dotenv
import os


load_dotenv()
# 🔐 Login credentials and Keycloak setup
USERNAME = os.getenv("USERNAME", "kaapana")
PASSWORD = os.getenv("PASSWORD", "admin")
PROTOCOL = os.getenv("PROTOCOL", "https")
HOST = os.environ["HOST"]
PORT = os.getenv("PORT", 443)
SSL_CHECK = False if os.getenv("SSL_CHECK", "False").lower == "false" else True
CLIENT_ID = os.getenv("CLIENT_ID", "kaapana")
CLIENT_SECRET = os.environ["CLIENT_SECRET"]


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
    cookies = {"Project": json.dumps({"name": project["name"], "id": project["id"]})}
    return headers, cookies


async def create_workflow(headers, cookies, payload):
    async with httpx.AsyncClient(base_url=BASE_URL, verify=False) as client:
        response = await client.post(
            "/workflow-api/v1/workflows", headers=headers, cookies=cookies, json=payload
        )
        assert response.status_code == 201
        data = response.json()
        return data


async def create_or_get_workflow(headers, cookies, payload):
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflows/{payload["identifier"]}/latest",
        headers=headers,
        cookies=cookies,
    )
    if response.status_code == 200:
        return response.json()
    else:
        return await create_workflow(headers, cookies, payload)


async def delete_workflow(headers, cookies, workflow_to_delete):
    response = await httpx.AsyncClient(verify=False).get(
        f"{BASE_URL}/workflow-api/v1/workflows/{workflow_to_delete}/latest",
        headers=headers,
        cookies=cookies,
    )
    assert response.status_code == 200
    version = response.json()["version"]
    response = await httpx.AsyncClient(verify=False).delete(
        f"{BASE_URL}/workflow-api/v1/workflows/{workflow_to_delete}/versions/{version}",
        headers=headers,
        cookies=cookies,
    )
    assert response.status_code == 204
