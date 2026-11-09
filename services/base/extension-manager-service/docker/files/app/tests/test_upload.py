import io
import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from v1.services import upload
from v1.services.database.models import RegisteredRepository

MOCK_EXTENSION_DIR = Path(__file__).resolve().parents[1] / "v1" / "mock_data" / "extension-v1"


def _manifest(**overrides) -> dict:
    manifest = json.loads((MOCK_EXTENSION_DIR / "extension_manifest.json").read_text())
    manifest["id"] = str(uuid4())
    manifest["version"] = "1.0.0"
    manifest.update(overrides)
    return manifest


WORKFLOW_FILES = {
    f"mock-workflow/{path.name}": path.read_bytes() for path in (MOCK_EXTENSION_DIR / "mock-workflow").iterdir()
}


def _archive(manifest: dict | list | None, files: dict[str, bytes] | None = None, links: dict[str, str] = {}) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        entries = dict(WORKFLOW_FILES if files is None else files)
        if manifest is not None:
            entries["extension_manifest.json"] = json.dumps(manifest).encode()
        for name, data in entries.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
        for name, target in links.items():
            info = tarfile.TarInfo(name=name)
            info.type = tarfile.SYMTYPE
            info.linkname = target
            tar.addfile(info)
    return buffer.getvalue()


def _with_content(**overrides) -> dict:
    manifest = _manifest()
    manifest["contents"][0].update(overrides)
    return manifest


async def _upload(client: AsyncClient, data: bytes, filename: str = "mock-workflow-extension-v1.0.0.tar.gz", **kwargs):
    return await client.post(
        "/extensions/upload",
        files={"file": (filename, data, "application/gzip")},
        **kwargs,
    )


@pytest.fixture(name="upload_dir", autouse=True)
def upload_dir_fixture(tmp_path: Path, monkeypatch) -> Path:
    monkeypatch.setattr(upload, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(upload, "WORK_DIR", tmp_path / "upload-work")
    return tmp_path / "uploads"


@pytest_asyncio.fixture(name="upload_repository", autouse=True)
async def upload_repository_fixture(session):
    session.add(
        RegisteredRepository(
            id=upload.UPLOAD_REPOSITORY_ID,
            name=upload.UPLOAD_REPOSITORY_NAME,
            description="",
            repository_url=upload.UPLOAD_REPOSITORY_URL,
            authentication="",
        )
    )
    await session.commit()


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
    return response.json()["id"]


@pytest.mark.asyncio
async def test_upload_installs_the_extension_into_the_upload_repository(
    client: AsyncClient, mocked_installer, upload_dir
):
    manifest = _manifest()

    response = await _upload(client, _archive(manifest))
    assert response.status_code == 201
    location = response.headers["Location"]

    extension = (await client.get(location)).json()
    tag = f"{manifest['id']}-v1.0.0"
    assert extension["status"] == "installed"
    assert extension["repository_id"] == str(upload.UPLOAD_REPOSITORY_ID)
    assert extension["tag"] == tag
    assert [content["status"] for content in extension["contents"]] == ["installed"]

    installed = mocked_installer.install_content.await_args.args[0]
    assert installed.name == "mock-workflow"
    assert str(installed.extension_id) == manifest["id"]
    assert [path.name for path in upload_dir.iterdir()] == [tag]

    response = await client.get(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}/extensions")
    assert response.json() == [tag]
    response = await client.get(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}/extensionManifests")
    assert [item["tag"] for item in response.json()] == [tag]


@pytest.mark.asyncio
async def test_uninstall_removes_the_uploaded_files(client: AsyncClient, mocked_installer, upload_dir, monkeypatch):
    monkeypatch.setattr("v1.routers.installation.background_jobs.asyncio.sleep", AsyncMock())
    response = await _upload(client, _archive(_manifest()))
    extension_id = response.json()["id"]

    response = await client.post(f"/extensions/{extension_id}/uninstall")
    assert response.status_code == 202
    assert list(upload_dir.iterdir()) == []
    assert (await client.get("/extensions")).json() == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("data", "filename", "detail"),
    [
        (b"not an archive", "broken.tar.gz", "not a valid .tar.gz archive"),
        (_archive(None), "no-manifest.tar.gz", "does not contain extension_manifest.json"),
        (_archive(_manifest(), files={}), "no-files.tar.gz", "does not contain mock-workflow/"),
        (_archive(_manifest(version="latest")), "bad-version.tar.gz", "manifest is invalid"),
        (_archive({k: v for k, v in _manifest().items() if k != "id"}), "no-id.tar.gz", "manifest has no id"),
        (_archive(_manifest(id="not-a-uuid")), "bad-id.tar.gz", "manifest is invalid"),
        (_archive(_manifest()), "extension.zip", "Only .tar.gz archives"),
        (
            _archive(_manifest(), files={"../outside.txt": b"x"}),
            "traversal.tar.gz",
            "forbidden entry",
        ),
        (
            _archive(_manifest(), links={"mock-workflow/link.py": "workflow_definition.py"}),
            "link.tar.gz",
            "contains the link mock-workflow/link.py",
        ),
        (
            _archive(_manifest(), files={**WORKFLOW_FILES, "mock-workflow/notes.txt": b"x"}),
            "unlisted.tar.gz",
            "files that the manifest does not list: mock-workflow/notes.txt",
        ),
        (_archive(_manifest(contents=[])), "no-contents.tar.gz", "lists no contents"),
        (_archive(_with_content(name="../mock-workflow")), "content-traversal.tar.gz", "must be a single folder name"),
        (
            _archive(_with_content(files=[{"path": "../../extension_manifest.json"}])),
            "file-traversal.tar.gz",
            "must be relative and stay in its folder",
        ),
        (
            _archive(_with_content(files=[{"path": "/etc/passwd"}])),
            "absolute-path.tar.gz",
            "must be relative and stay in its folder",
        ),
        (
            _archive({**_manifest(), "contents": _manifest()["contents"] * 2}),
            "duplicate-content.tar.gz",
            "content name mock-workflow is used more than once",
        ),
        (
            _archive(None, files={**WORKFLOW_FILES, "extension_manifest.json": b"{"}),
            "bad-json.tar.gz",
            "not valid JSON",
        ),
        (_archive([]), "json-list.tar.gz", "must contain a JSON object"),
        (_archive(_manifest(version="1.0." + "0" * 120)), "long-tag.tar.gz", "longer than 128 characters"),
    ],
)
async def test_upload_rejects_invalid_archives(
    client: AsyncClient, mocked_installer, upload_dir, data, filename, detail
):
    response = await _upload(client, data, filename=filename)
    assert response.status_code == 400
    assert detail in response.json()["detail"]
    assert (await client.get("/extensions")).json() == []
    assert not upload_dir.exists() or list(upload_dir.iterdir()) == []
    assert (await client.get(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}/extensions")).json() == []
    mocked_installer.install_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_upload_reports_every_schema_error(client: AsyncClient):
    response = await _upload(client, _archive(_manifest(name="bad name", version="latest")))
    assert response.status_code == 400
    assert "name: 'bad name' does not match" in response.json()["detail"]
    assert "version: 'latest' does not match" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "value", "detail"),
    [
        ("MAX_EXTRACTED_BYTES", 10, "unpacks to more than"),
        ("MAX_ARCHIVE_ENTRIES", 2, "has more than 2 entries"),
    ],
)
async def test_upload_rejects_archives_above_the_unpack_limits(client: AsyncClient, monkeypatch, limit, value, detail):
    monkeypatch.setattr(upload, limit, value)

    response = await _upload(client, _archive(_manifest()))
    assert response.status_code == 400
    assert detail in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("files", "detail"),
    [
        ({**WORKFLOW_FILES, "mock-workflow/workflow.json": b"{"}, "Invalid JSON format in workflow.json"),
        ({**WORKFLOW_FILES, "mock-workflow/workflow.json": b'{"title": ""}'}, "must contain a non-empty title"),
        ({**WORKFLOW_FILES, "mock-workflow/workflow_definition.py": b"  "}, "workflow_definition.py is empty"),
    ],
)
async def test_upload_rejects_invalid_workflow_content(client: AsyncClient, files, detail):
    response = await _upload(client, _archive(_manifest(), files=files))
    assert response.status_code == 400
    assert response.json()["detail"].startswith("The content mock-workflow is invalid:")
    assert detail in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_unknown_content_types(client: AsyncClient):
    manifest = _manifest()
    manifest["contents"][0]["contentType"] = "helm-v1"

    response = await _upload(client, _archive(manifest))
    assert response.status_code == 400
    assert response.json()["detail"] == "No installer found for content type helm-v1"


@pytest.mark.asyncio
async def test_upload_rejects_archives_above_the_size_limit(client: AsyncClient, monkeypatch):
    monkeypatch.setattr(upload, "MAX_UPLOAD_BYTES", 10)

    response = await _upload(client, _archive(_manifest()))
    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_rejects_an_extension_that_is_already_installed(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    assert (await _upload(client, _archive(manifest))).status_code == 201

    response = await _upload(client, _archive(manifest))
    assert response.status_code == 409
    assert "in status installed" in response.json()["detail"]
    assert len((await client.get("/extensions")).json()) == 1


@pytest.mark.asyncio
async def test_upload_retries_a_failed_installation(client: AsyncClient, mocked_installer, upload_dir):
    manifest = _manifest()
    install_content = mocked_installer.install_content
    mocked_installer.install_content = AsyncMock(side_effect=RuntimeError("workflow api down"))

    with pytest.raises(ExceptionGroup):
        await _upload(client, _archive(manifest))
    [failed] = (await client.get("/extensions")).json()
    assert failed["status"] == "installing_failed"
    location = f"/extensions/{failed['id']}"

    mocked_installer.install_content = install_content
    response = await _upload(client, _archive(manifest))
    assert response.status_code == 201
    assert response.headers["Location"] == location
    assert (await client.get(location)).json()["status"] == "installed"


@pytest.mark.asyncio
async def test_failed_upload_can_be_retried_from_the_upload_repository(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    install_content = mocked_installer.install_content
    mocked_installer.install_content = AsyncMock(side_effect=RuntimeError("workflow api down"))
    with pytest.raises(ExceptionGroup):
        await _upload(client, _archive(manifest))

    mocked_installer.install_content = install_content
    response = await client.post(
        f"/extensions/install?repository_id={upload.UPLOAD_REPOSITORY_ID}&tag={manifest['id']}-v1.0.0"
    )
    assert response.status_code == 201
    assert (await client.get(response.headers["Location"])).json()["status"] == "installed"


@pytest.mark.asyncio
async def test_failed_upload_with_a_different_manifest_is_rejected(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    mocked_installer.install_content = AsyncMock(side_effect=RuntimeError("workflow api down"))
    with pytest.raises(ExceptionGroup):
        await _upload(client, _archive(manifest))

    response = await _upload(client, _archive({**manifest, "name": "renamed"}))
    assert response.status_code == 409
    assert "different manifest" in response.json()["detail"]


@pytest.mark.asyncio
async def test_the_same_tag_cannot_be_installed_from_two_repositories(client: AsyncClient, mocked_installer):
    first = await _create_repository(client, "First")
    second = await _create_repository(client, "Second")
    assert (await client.post(f"/extensions/install?repository_id={first}&tag=extension-v1")).status_code == 201

    response = await client.post(f"/extensions/install?repository_id={second}&tag=extension-v1")
    assert response.status_code == 409
    assert "already installed from the repository First" in response.json()["detail"]


@pytest.mark.asyncio
async def test_the_upload_repository_cannot_be_changed_or_removed(client: AsyncClient):
    [repository] = (await client.get("/repositories")).json()
    assert repository["built_in"] is True
    assert repository["name"] == "Upload"

    response = await client.put(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}", json={"name": "Other"})
    assert response.status_code == 409
    response = await client.delete(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}")
    assert response.status_code == 409
    assert (await client.get(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}")).json()["name"] == "Upload"
