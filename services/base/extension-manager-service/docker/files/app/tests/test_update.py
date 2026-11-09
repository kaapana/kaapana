import json
import shutil
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from v1.services.database import crud
from v1.services.database.models import ExtensionStatus
from v1.services.oci.mock_service import ociService as MockOciService

MOCK_EXTENSION_DIR = Path(__file__).resolve().parents[1] / "v1" / "mock_data" / "extension-v1"


def _add_version(repository_dir: Path, tag: str, version: str, extra_content: bool = False, content_type: str = ""):
    extension_dir = repository_dir / tag
    shutil.copytree(MOCK_EXTENSION_DIR, extension_dir)
    manifest = json.loads((extension_dir / "extension_manifest.json").read_text())
    manifest["version"] = version
    if content_type:
        manifest["contents"][0]["contentType"] = content_type
    if extra_content:
        shutil.copytree(extension_dir / "mock-workflow", extension_dir / "extra-workflow")
        manifest["contents"].append({**manifest["contents"][0], "name": "extra-workflow"})
    (extension_dir / "extension_manifest.json").write_text(json.dumps(manifest))


@pytest.fixture(name="mock_repository", autouse=True)
def mock_repository_fixture(tmp_path: Path, monkeypatch):
    repository_dir = tmp_path / "repository"
    _add_version(repository_dir, "extension-v0", "0.9.0")
    _add_version(repository_dir, "extension-v1", "1.0.0")
    _add_version(repository_dir, "extension-v2", "1.1.0", extra_content=True)
    _add_version(repository_dir, "extension-v3", "1.2.0", content_type="other-v1")
    original_init = MockOciService.__init__

    def init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.extension_dir = repository_dir

    monkeypatch.setattr(MockOciService, "__init__", init)


async def _create_repository(client: AsyncClient, name: str = "Test Repository") -> str:
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
    return response.headers["Location"].split("/")[-1]


async def _install(client: AsyncClient, repository_id: str, tag: str):
    return await client.post(f"/extensions/install?repository_id={repository_id}&tag={tag}")


@pytest.mark.asyncio
async def test_a_newer_version_updates_the_installed_extension(client: AsyncClient, mocked_installer):
    repository_id = await _create_repository(client)
    location = (await _install(client, repository_id, "extension-v1")).headers["Location"]

    response = await _install(client, repository_id, "extension-v2")
    assert response.status_code == 202
    assert response.headers["Location"] == location

    extension = (await client.get(location)).json()
    assert extension["status"] == "installed"
    assert extension["tag"] == "extension-v2"
    assert extension["manifest"]["version"] == "1.1.0"
    assert extension["pending_update"] is None
    assert {content["name"]: content["applied_version"] for content in extension["contents"]} == {
        "mock-workflow": "1.1.0",
        "extra-workflow": "1.1.0",
    }
    assert mocked_installer.update_content.await_args.args[0].name == "mock-workflow"
    assert mocked_installer.install_content.await_args.args[0].name == "extra-workflow"
    assert len((await client.get("/extensions")).json()) == 1


@pytest.mark.asyncio
async def test_an_older_version_conflicts(client: AsyncClient, mocked_installer):
    repository_id = await _create_repository(client)
    await _install(client, repository_id, "extension-v1")

    response = await _install(client, repository_id, "extension-v0")
    assert response.status_code == 409
    assert "downgrading to 0.9.0 is not supported" in response.json()["detail"]


@pytest.mark.asyncio
async def test_a_newer_version_from_another_repository_conflicts(client: AsyncClient, mocked_installer):
    first = await _create_repository(client, "First")
    second = await _create_repository(client, "Second")
    await _install(client, first, "extension-v1")

    response = await _install(client, second, "extension-v2")
    assert response.status_code == 409
    assert "from another repository" in response.json()["detail"]


@pytest.mark.asyncio
async def test_a_changed_content_type_is_rejected(client: AsyncClient, mocked_installer):
    repository_id = await _create_repository(client)
    await _install(client, repository_id, "extension-v1")

    response = await _install(client, repository_id, "extension-v3")
    assert response.status_code == 400
    assert "changes its type" in response.json()["detail"]


@pytest.mark.asyncio
async def test_a_failed_update_shows_its_target_and_a_retry_only_touches_old_contents(
    client: AsyncClient, mocked_installer
):
    repository_id = await _create_repository(client)
    location = (await _install(client, repository_id, "extension-v1")).headers["Location"]
    update_content = mocked_installer.update_content
    mocked_installer.update_content = AsyncMock(side_effect=RuntimeError("workflow api down"))

    with pytest.raises(ExceptionGroup):
        await _install(client, repository_id, "extension-v2")

    extension = (await client.get(location)).json()
    assert extension["status"] == "update_failed"
    assert extension["manifest"]["version"] == "1.0.0"
    assert extension["pending_update"]["manifest"]["version"] == "1.1.0"
    assert {content["name"]: (content["status"], content["applied_version"]) for content in extension["contents"]} == {
        "mock-workflow": ("update_failed", "1.0.0"),
        "extra-workflow": ("installed", "1.1.0"),
    }

    mocked_installer.update_content = update_content
    mocked_installer.install_content.reset_mock()
    response = await _install(client, repository_id, "extension-v2")
    assert response.status_code == 202

    extension = (await client.get(location)).json()
    assert extension["status"] == "installed"
    assert extension["manifest"]["version"] == "1.1.0"
    mocked_installer.update_content.assert_awaited_once()
    mocked_installer.install_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_an_uninstalled_row_with_the_target_tag_does_not_block_the_update(
    client: AsyncClient, session: AsyncSession, mocked_installer
):
    repository_id = await _create_repository(client)
    location = (await _install(client, repository_id, "extension-v1")).headers["Location"]
    manifest = (await client.get(location)).json()["manifest"]
    db_uninstalled = await crud.create_extension(
        session, repository_id=UUID(repository_id), tag="extension-v2", manifest={**manifest, "version": "1.1.0"}
    )
    db_uninstalled.status = ExtensionStatus.UNINSTALLED
    await session.commit()

    response = await _install(client, repository_id, "extension-v2")
    assert response.status_code == 202

    extension = (await client.get(location)).json()
    assert extension["status"] == "installed"
    assert extension["tag"] == "extension-v2"
    assert len((await client.get("/extensions")).json()) == 1
