import io
import json
import tarfile
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from conftest import UPLOAD_REGISTRY_URL
from httpx import AsyncClient
from v1.services import upload
from v1.services.database import crud
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


def _archive_with_entry(info: tarfile.TarInfo) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.addfile(info)
    return buffer.getvalue()


def _fifo(name: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name=name)
    info.type = tarfile.FIFOTYPE
    return info


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


@pytest_asyncio.fixture(name="upload_repository", autouse=True)
async def upload_repository_fixture(session):
    session.add(
        RegisteredRepository(
            id=upload.UPLOAD_REPOSITORY_ID,
            name="Upload",
            description="",
            repository_url=UPLOAD_REGISTRY_URL,
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


def _tag(manifest: dict) -> str:
    return f"{manifest['id']}-v{manifest['version']}"


async def _install(client: AsyncClient, tag: str):
    return await client.post(f"/extensions/install?repository_id={upload.UPLOAD_REPOSITORY_ID}&tag={tag}")


async def _catalog(client: AsyncClient) -> list[str]:
    return (await client.get(f"/repositories/{upload.UPLOAD_REPOSITORY_ID}/extensions")).json()


@pytest.mark.asyncio
async def test_upload_stores_the_extension_without_installing_it(client: AsyncClient, mocked_installer):
    manifest = _manifest()

    response = await _upload(client, _archive(manifest))
    assert response.status_code == 201
    tag = _tag(manifest)
    assert response.json() == {
        "repository_id": str(upload.UPLOAD_REPOSITORY_ID),
        "tag": tag,
        "manifest": response.json()["manifest"],
    }
    assert response.json()["manifest"]["id"] == manifest["id"]
    assert (await client.get(response.headers["Location"])).json()[0]["tag"] == tag

    assert (await client.get("/extensions")).json() == []
    mocked_installer.install_content.assert_not_awaited()
    assert await _catalog(client) == [tag]


@pytest.mark.asyncio
async def test_an_uploaded_extension_is_installed_from_the_upload_repository(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    await _upload(client, _archive(manifest))

    response = await _install(client, _tag(manifest))
    assert response.status_code == 201
    extension = (await client.get(response.headers["Location"])).json()
    assert extension["status"] == "installed"
    assert extension["repository_id"] == str(upload.UPLOAD_REPOSITORY_ID)
    installed = mocked_installer.install_content.await_args.args[0]
    assert installed.name == "mock-workflow"
    assert str(installed.extension_id) == manifest["id"]


@pytest.mark.asyncio
async def test_uninstall_keeps_the_upload(client: AsyncClient, mocked_installer, monkeypatch):
    monkeypatch.setattr("v1.routers.installation.background_jobs.asyncio.sleep", AsyncMock())
    manifest = _manifest()
    await _upload(client, _archive(manifest))
    extension_id = (await _install(client, _tag(manifest))).json()["id"]

    response = await client.post(f"/extensions/{extension_id}/uninstall")
    assert response.status_code == 202
    assert (await client.get("/extensions")).json() == []
    assert await _catalog(client) == [_tag(manifest)]
    assert (await _install(client, _tag(manifest))).status_code == 201


@pytest.mark.asyncio
async def test_removing_an_upload_keeps_the_installation(client: AsyncClient, mocked_installer, monkeypatch):
    monkeypatch.setattr("v1.routers.installation.background_jobs.asyncio.sleep", AsyncMock())
    manifest = _manifest()
    tag = _tag(manifest)
    await _upload(client, _archive(manifest))
    extension_id = (await _install(client, tag)).json()["id"]

    response = await client.delete(f"/extensions/uploads/{tag}")
    assert response.status_code == 204
    assert await _catalog(client) == []
    assert (await client.get(f"/extensions/{extension_id}")).json()["status"] == "installed"

    assert (await client.post(f"/extensions/{extension_id}/uninstall")).status_code == 202
    mocked_installer.uninstall_content.assert_awaited()
    assert (await client.get("/extensions")).json() == []


@pytest.mark.asyncio
async def test_removing_an_unknown_upload_returns_404(client: AsyncClient):
    response = await client.delete("/extensions/uploads/missing-v1")
    assert response.status_code == 404
    assert "missing-v1 was not uploaded" in response.json()["detail"]


@pytest.mark.asyncio
@pytest.mark.parametrize("extension_status", ["pending", "pulling"])
async def test_an_upload_cannot_be_changed_while_it_is_pulled(client: AsyncClient, session, extension_status):
    manifest = _manifest()
    tag = _tag(manifest)
    await _upload(client, _archive(manifest))
    db_extension = await crud.create_extension(
        session, repository_id=upload.UPLOAD_REPOSITORY_ID, tag=tag, manifest=manifest
    )
    db_extension.status = extension_status
    await session.commit()

    response = await client.delete(f"/extensions/uploads/{tag}")
    assert response.status_code == 409
    assert "is being installed" in response.json()["detail"]
    response = await _upload(client, _archive(manifest))
    assert response.status_code == 409
    assert await _catalog(client) == [tag]


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
        (_archive(None, files={}), "empty.tar.gz", "The archive is empty."),
        (_archive_with_entry(_fifo("mock-workflow/pipe")), "fifo.tar.gz", "is neither a file nor a folder"),
        (
            _archive(_with_content(contentType="x" * 256)),
            "long-content-type.tar.gz",
            "content type " + "x" * 256 + " is longer than 255 characters",
        ),
    ],
)
async def test_upload_rejects_invalid_archives(client: AsyncClient, mocked_installer, data, filename, detail):
    response = await _upload(client, data, filename=filename)
    assert response.status_code == 400
    assert detail in response.json()["detail"]
    assert (await client.get("/extensions")).json() == []
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
        ({**WORKFLOW_FILES, "mock-workflow/workflow.json": b"[]"}, "must contain a JSON object"),
        ({**WORKFLOW_FILES, "mock-workflow/workflow.json": b'{"title": 1}'}, "must contain a non-empty title"),
        ({**WORKFLOW_FILES, "mock-workflow/workflow_definition.py": b"\xff\xfe"}, "must be UTF-8 text"),
    ],
)
async def test_upload_rejects_invalid_workflow_content(client: AsyncClient, files, detail):
    response = await _upload(client, _archive(_manifest(), files=files))
    assert response.status_code == 400
    assert response.json()["detail"].startswith("The content mock-workflow is invalid:")
    assert detail in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_rejects_workflow_content_without_its_required_files(client: AsyncClient):
    manifest = _with_content(files=[{"path": "workflow_definition.py"}])
    files = {"mock-workflow/workflow_definition.py": WORKFLOW_FILES["mock-workflow/workflow_definition.py"]}

    response = await _upload(client, _archive(manifest, files=files))
    assert response.status_code == 400
    assert "Required file not found for workflow content" in response.json()["detail"]
    assert "workflow.json" in response.json()["detail"]


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
async def test_uploading_the_same_extension_again_replaces_it(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    assert (await _upload(client, _archive(manifest))).status_code == 201
    assert (await _install(client, _tag(manifest))).status_code == 201

    response = await _upload(client, _archive(manifest))
    assert response.status_code == 201
    assert await _catalog(client) == [_tag(manifest)]
    assert len((await client.get("/extensions")).json()) == 1


@pytest.mark.asyncio
async def test_upload_with_a_different_manifest_is_rejected_while_installed(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    await _upload(client, _archive(manifest))
    await _install(client, _tag(manifest))

    response = await _upload(client, _archive({**manifest, "name": "renamed"}))
    assert response.status_code == 409
    assert "installed with a different manifest" in response.json()["detail"]


@pytest.mark.asyncio
async def test_upload_with_a_different_manifest_replaces_an_uninstalled_one(
    client: AsyncClient, mocked_installer, monkeypatch
):
    monkeypatch.setattr("v1.routers.installation.background_jobs.asyncio.sleep", AsyncMock())
    manifest = _manifest()
    await _upload(client, _archive(manifest))
    extension_id = (await _install(client, _tag(manifest))).json()["id"]
    await client.post(f"/extensions/{extension_id}/uninstall")

    response = await _upload(client, _archive({**manifest, "name": "renamed"}))
    assert response.status_code == 201
    assert response.json()["manifest"]["name"] == "renamed"


@pytest.mark.asyncio
async def test_a_failed_installation_can_be_retried_from_the_upload_repository(client: AsyncClient, mocked_installer):
    manifest = _manifest()
    await _upload(client, _archive(manifest))
    install_content = mocked_installer.install_content
    mocked_installer.install_content = AsyncMock(side_effect=RuntimeError("workflow api down"))
    with pytest.raises(ExceptionGroup):
        await _install(client, _tag(manifest))
    [failed] = (await client.get("/extensions")).json()
    assert failed["status"] == "installing_failed"

    mocked_installer.install_content = install_content
    response = await _install(client, _tag(manifest))
    assert response.status_code == 201
    assert response.headers["Location"] == f"/extensions/{failed['id']}"
    assert (await client.get(response.headers["Location"])).json()["status"] == "installed"


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


@pytest.mark.asyncio
async def test_an_upload_cannot_be_installed_while_installed_from_another_repository(
    client: AsyncClient, session, mocked_installer
):
    repository_id = await _create_repository(client)
    manifest = _manifest()
    await crud.create_extension(session, repository_id=UUID(repository_id), tag=_tag(manifest), manifest=manifest)

    assert (await _upload(client, _archive(manifest))).status_code == 201
    response = await _install(client, _tag(manifest))
    assert response.status_code == 409
    assert "already installed from the repository Test Repository" in response.json()["detail"]
    mocked_installer.install_content.assert_not_awaited()


@pytest.mark.asyncio
async def test_installing_an_unknown_tag_from_the_upload_repository_returns_404(client: AsyncClient):
    response = await _install(client, "missing-v1")
    assert response.status_code == 404
    assert UPLOAD_REGISTRY_URL in response.json()["detail"]
