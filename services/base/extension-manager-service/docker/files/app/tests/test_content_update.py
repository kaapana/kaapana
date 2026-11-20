from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from v1.services.content_update import apply_content_changes
from v1.services.database import crud, models
from v1.services.dispatch.content import InstallationResult
from v1.services.oci.models import Content, ExtensionManifest

EXTENSION_ID = uuid4()


def _manifest(version: str, names: list[str]) -> ExtensionManifest:
    return ExtensionManifest(
        id=EXTENSION_ID,
        name="extension",
        version=version,
        contents=[Content(name=name, contentType="workflow-v1", files=[]) for name in names],
        dependencies=[],
    )


async def _installed_extension(session: AsyncSession, names: list[str]) -> models.Extension:
    manifest = _manifest("1.0.0", names)
    db_repository = await crud.create_registered_repository(
        session, name="repository", description="", repository_url="https://example.com/oci", authentication=""
    )
    db_extension = await crud.create_extension(
        session, repository_id=db_repository.id, tag="extension-v1.0.0", manifest=manifest.model_dump(mode="json")
    )
    for name in names:
        db_content = await crud.create_content(
            session, extension_id=db_extension.id, content_type="workflow-v1", name=name
        )
        await crud.update_content(session, content_id=db_content.id, status=models.ContentStatus.INSTALLING)
        await crud.update_content(
            session,
            content_id=db_content.id,
            status=models.ContentStatus.INSTALLED,
            location=f"/workflows/{name}",
            applied_version="1.0.0",
        )
    return await _reload(session, db_extension.id)


async def _reload(session: AsyncSession, extension_id: UUID) -> models.Extension:
    session.expire_all()
    db_extension = await crud.get_extension(session, extension_id=extension_id)
    assert db_extension is not None
    return db_extension


async def _contents(session: AsyncSession, extension_id: UUID) -> dict[str, tuple[str, str | None]]:
    result = await session.execute(select(models.Content).where(models.Content.extension_id == extension_id))
    return {content.name: (content.status, content.applied_version) for content in result.scalars()}


@pytest.mark.asyncio
async def test_update_installs_updates_and_uninstalls_contents(session: AsyncSession, mocked_installer, tmp_path: Path):
    db_extension = await _installed_extension(session, ["kept", "removed"])

    await apply_content_changes(session, db_extension, _manifest("2.0.0", ["kept", "added"]), tmp_path)

    assert await _contents(session, db_extension.id) == {
        "kept": (models.ContentStatus.INSTALLED, "2.0.0"),
        "added": (models.ContentStatus.INSTALLED, "2.0.0"),
    }
    updated = mocked_installer.update_content.await_args.args[0]
    assert (updated.name, updated.location, updated.extension_version) == ("kept", "/workflows/kept", "2.0.0")
    assert mocked_installer.install_content.await_args.args[0].name == "added"
    assert mocked_installer.uninstall_content.await_args.args[0].name == "removed"


@pytest.mark.asyncio
async def test_failed_content_keeps_its_version_and_only_it_is_retried(
    session: AsyncSession, mocked_installer, tmp_path: Path
):
    db_extension = await _installed_extension(session, ["works", "fails"])
    target = _manifest("2.0.0", ["works", "fails"])

    def update(content):
        if content.name == "fails":
            raise RuntimeError("workflow API rejected the definition")
        return InstallationResult(success=True, location=content.location)

    mocked_installer.update_content.side_effect = update
    with pytest.raises(ExceptionGroup):
        await apply_content_changes(session, db_extension, target, tmp_path)

    assert await _contents(session, db_extension.id) == {
        "works": (models.ContentStatus.INSTALLED, "2.0.0"),
        "fails": (models.ContentStatus.UPDATE_FAILED, "1.0.0"),
    }

    mocked_installer.update_content.reset_mock(side_effect=True)
    await apply_content_changes(session, await _reload(session, db_extension.id), target, tmp_path)

    assert [call.args[0].name for call in mocked_installer.update_content.await_args_list] == ["fails"]
    assert await _contents(session, db_extension.id) == {
        "works": (models.ContentStatus.INSTALLED, "2.0.0"),
        "fails": (models.ContentStatus.INSTALLED, "2.0.0"),
    }
