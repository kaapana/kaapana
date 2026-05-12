import pytest
from httpx import AsyncClient
import json


@pytest.mark.asyncio
async def test_read_repositories(client: AsyncClient):
    response = await client.get("/repositories")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_post_repository(client: AsyncClient):
    response = await client.post(
        "/repositories",
        json={
            "name": "Test Repository",
            "description": "",
            "authentication": "",
            "repository_url": "https://example.com/oci",
        },
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")


@pytest.mark.asyncio
async def test_post_repository_get_repository(client: AsyncClient):
    repo_payload = {
        "name": "Test Repository",
        "description": "",
        "authentication": "",
        "repository_url": "https://example.com/oci",
    }

    response = await client.post(
        "/repositories",
        json=repo_payload,
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")

    response = await client.get(response.headers["Location"])
    assert response.status_code == 200
    assert response.json() == {
        "id": response.json()["id"],
        "name": repo_payload["name"],
        "description": repo_payload["description"],
        "repository_url": repo_payload["repository_url"],
    }


@pytest.mark.asyncio
async def test_post_repository_delete_repository_get_404(client: AsyncClient):
    repo_payload = {
        "name": "Test Repository",
        "description": "",
        "authentication": "",
        "repository_url": "https://example.com/oci",
    }

    response = await client.post(
        "/repositories",
        json=repo_payload,
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")
    location = response.headers["Location"]

    response = await client.delete(location)
    assert response.status_code == 204

    response = await client.get(location)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_conflict_repository(client: AsyncClient):
    repo_payload = {
        "name": "Test Repository",
        "description": "",
        "authentication": "",
        "repository_url": "https://example.com/oci",
    }

    response = await client.post(
        "/repositories",
        json=repo_payload,
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")
    location = response.headers["Location"]

    response = await client.post(
        "/repositories",
        json=repo_payload,
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_post_repository_get_extensions_get_manifests(client: AsyncClient):
    response = await client.post(
        "/repositories",
        json={
            "name": "Test Repository",
            "description": "",
            "authentication": "",
            "repository_url": "https://example.com/oci",
        },
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")

    location = response.headers["Location"]
    repository_id = location.split("/")[-1]

    response = await client.get(location + "/extensions")
    assert response.status_code == 200
    assert response.json() == ["extension-v1"]

    response = await client.get(location + "/extensionManifests")
    assert response.status_code == 200
    with open("v1/mock_data/extension-v1/manifest.json") as f:
        manifest = json.load(f)
    assert response.json() == [
        {
            "tag": "extension-v1",
            "repository_id": repository_id,
            "manifest": manifest,
        }
    ]
