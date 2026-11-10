import asyncio
import time
from uuid import UUID, uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from v1.routers.installation.background_jobs import install_extension_background_task
from v1.services.database import crud, database


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
async def test_post_repo_read_extensions_install_extension(client: AsyncClient, mocked_installer):
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

    response = await client.post(f"/extensions/install?repository_id={repository_id}&tag={tag}")
    assert response.status_code == 201
    extension_location = response.headers["Location"]

    response = await client.get(extension_location)
    assert response.status_code == 200
    assert response.json()["tag"] == tag
    assert response.json()["repository_id"] == repository_id
    assert response.json()["status"] == "installed"


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

    response = await client.post(f"/extensions/install?repository_id={repository_id}&tag={tag}")
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
        assert await crud.get_content(session=session, content_id=id) is None


async def _install_from_new_repository(client: AsyncClient, name: str = "Test Repository"):
    response = await client.post(
        "/repositories",
        json={
            "name": name,
            "description": "",
            "username": "test",
            "password": "test",
            "repository_url": "https://example.com/oci",
        },
    )
    assert response.status_code == 201
    repository_location = response.headers["Location"]
    repository_id = repository_location.split("/")[-1]

    response = await client.get(repository_location + "/extensions")
    tag = response.json()[0]

    response = await client.post(f"/extensions/install?repository_id={repository_id}&tag={tag}")
    assert response.status_code == 201
    return repository_location, repository_id, tag, response.headers["Location"]


@pytest.mark.asyncio
async def test_extension_keeps_the_name_and_url_of_its_repository(client: AsyncClient, mocked_installer):
    repository_location, _, _, extension_location = await _install_from_new_repository(client)

    response = await client.get(extension_location)
    assert response.json()["repository_name"] == "Test Repository"
    assert response.json()["repository_url"] == "https://example.com/oci"

    response = await client.put(repository_location, json={"name": "Renamed Repository"})
    assert response.status_code == 200

    response = await client.get(extension_location)
    assert response.json()["repository_name"] == "Renamed Repository"


@pytest.mark.asyncio
async def test_delete_repository_detaches_its_installed_extensions(client: AsyncClient, mocked_installer, monkeypatch):
    async def fast_sleep(seconds):
        pass

    monkeypatch.setattr(asyncio, "sleep", fast_sleep)

    repository_location, repository_id, tag, extension_location = await _install_from_new_repository(client)

    response = await client.delete(repository_location)
    assert response.status_code == 204
    mocked_installer.uninstall_content.assert_not_awaited()

    response = await client.get(extension_location)
    assert response.status_code == 200
    extension = response.json()
    assert extension["repository_id"] is None
    assert extension["repository_name"] == "Test Repository"
    assert extension["repository_url"] == "https://example.com/oci"
    assert extension["status"] == "installed"

    response = await client.post(f"/extensions/install?repository_id={repository_id}&tag={tag}")
    assert response.status_code == 404

    response = await client.post(
        "/repositories",
        json={
            "name": "Same URL",
            "description": "",
            "username": "test",
            "password": "test",
            "repository_url": "https://example.com/oci",
        },
    )
    same_url_repository_id = response.headers["Location"].split("/")[-1]
    response = await client.get(extension_location)
    assert response.json()["repository_id"] is None

    response = await client.post(f"/extensions/install?repository_id={same_url_repository_id}&tag={tag}")
    assert response.status_code == 409
    assert "Test Repository" in response.json()["detail"]

    response = await client.post(extension_location + "/uninstall")
    assert response.status_code == 202
    mocked_installer.uninstall_content.assert_awaited()

    response = await client.get(extension_location)
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_a_download_whose_repository_was_removed_fails_and_can_be_uninstalled(
    client: AsyncClient, session: AsyncSession, mocked_installer, monkeypatch
):
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
    repository_location = response.headers["Location"]
    db_repository = await crud.get_registered_repository(session, UUID(repository_location.split("/")[-1]))
    db_extension = await crud.create_extension(
        session,
        repository=db_repository,
        tag="downloading",
        manifest={"id": str(uuid4()), "name": "downloading", "version": "1.0.0", "contents": [], "dependencies": []},
    )

    response = await client.delete(repository_location)
    assert response.status_code == 204

    await install_extension_background_task(db_extension.id)

    async with database.async_session() as fresh_session:
        detached = await crud.get_extension(fresh_session, extension_id=db_extension.id)
    assert detached.repository_id is None
    assert detached.status == crud.ExtensionStatus.PULLING_FAILED

    response = await client.post(f"/extensions/{db_extension.id}/uninstall")
    assert response.status_code == 202
