import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
import json
import time
import asyncio
from uuid import uuid4, UUID


@pytest.mark.asyncio
async def test_read_extensions(client: AsyncClient):
    response = await client.get("/extensions")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_read_uninstall_extension_404(client: AsyncClient):
    response = await client.get(f"/extensions/{uuid4()}")
    assert response.status_code == 404

    response = await client.post(f"/extensions/{uuid4()}/uninstall")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_post_repo_read_extensions_install_extension(
    client: AsyncClient, mocked_installer
):
    response = await client.post(
        "/repositories",
        json={
            "name": "Test Repository",
            "description": "",
            "username": "test",
            "password": "test",
            "repository_url": "https://example.com/oci",
        },
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")
    location = response.headers["Location"]

    response = await client.get(location)
    assert response.status_code == 200
    repository_id = response.json()["id"]

    response = await client.get(location + "/extensions")
    assert response.status_code == 200
    tag = response.json()[0]

    response = await client.post(
        f"/extensions/install?repository_id={repository_id}&tag={tag}"
    )
    assert response.status_code == 201
    extension_location = response.headers["Location"]

    response = await client.get(extension_location)
    assert response.status_code == 200
    assert response.json()["tag"] == tag
    assert response.json()["repository_id"] == repository_id
    assert response.json()["status"] == "installed"


from v1.services.database import crud


@pytest.mark.asyncio
async def test_post_repo_read_extensions_install_extension_uninstall_extension(
    client: AsyncClient, session: AsyncSession, mocked_installer, monkeypatch
):

    ### Patch asyncio.sleep
    ### Otherwise the background task uninstall takes 30 seconds
    async def fast_sleep(seconds):
        pass

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    response = await client.post(
        "/repositories",
        json={
            "name": "Test Repository",
            "description": "",
            "username": "test",
            "password": "test",
            "repository_url": "https://example.com/oci",
        },
    )
    assert response.status_code == 201
    assert response.headers.get("Location").startswith("/repositories/")
    location = response.headers["Location"]

    response = await client.get(location)
    assert response.status_code == 200
    repository_id = response.json()["id"]

    response = await client.get(location + "/extensions")
    assert response.status_code == 200
    tag = response.json()[0]

    response = await client.post(
        f"/extensions/install?repository_id={repository_id}&tag={tag}"
    )
    assert response.status_code == 201
    extension_location = response.headers["Location"]

    response = await client.get(extension_location)
    extension = response.json()
    assert response.status_code == 200
    assert extension["tag"] == tag
    assert extension["repository_id"] == repository_id
    assert extension["status"] == "installed"
    db_extension = await crud.get_extension(session, extension_id=UUID(extension["id"]))
    assert db_extension is not None
    content_ids = [content.id for content in db_extension.contents]
    t0 = time.time()
    response = await client.post(extension_location + "/uninstall")
    assert response.status_code == 202

    assert abs(t0 - time.time()) < 2

    response = await client.get(extension_location)
    assert response.status_code == 404

    ### Check that database entries were deleted
    db_extension = await crud.get_extension(session, extension_id=UUID(extension["id"]))
    assert db_extension is None

    for id in content_ids:
        assert await crud.get_content(session=session, content_id=id) == None
