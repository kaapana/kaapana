from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from v1.services import dispatch
from v1.services.content_changes import ContentAction, InstalledContentState, plan_content_changes
from v1.services.database import crud, models
from v1.services.logger import get_logger
from v1.services.oci.models import ExtensionManifest

logger = get_logger(__name__)


def plan_extension_update(db_extension: models.Extension, target: ExtensionManifest) -> list[tuple[str, ContentAction]]:
    installed = [
        InstalledContentState(
            name=content.name,
            content_type=content.content_type,
            status=content.status,
            applied_version=content.applied_version,
        )
        for content in db_extension.contents
    ]
    return plan_content_changes(installed, target)


async def apply_content_changes(
    db: AsyncSession,
    db_extension: models.Extension,
    target: ExtensionManifest,
    extension_path: Path,
) -> None:
    """A content that fails keeps its last applied version; all failures are raised together as an ExceptionGroup at the end."""
    contents_by_name = {content.name: content for content in db_extension.contents}
    target_by_name = {content.name: content for content in target.contents}
    content_exceptions = []

    for name, action in plan_extension_update(db_extension, target):
        if action == ContentAction.SKIP:
            continue
        try:
            if action == ContentAction.INSTALL:
                db_content = contents_by_name.get(name) or await crud.create_content(
                    db,
                    extension_id=db_extension.id,
                    content_type=target_by_name[name].contentType,
                    name=name,
                )
                await _install(db, db_content, target, extension_path)
            elif action == ContentAction.UPDATE:
                await _update(db, contents_by_name[name], target, extension_path)
            else:
                await _uninstall(db, contents_by_name[name])
        except Exception as e:
            logger.error("Failed to %s content '%s': %s", action, name, e, exc_info=True)
            content_exceptions.append(e)

    if content_exceptions:
        raise ExceptionGroup("One or more content updates failed", content_exceptions)


def _content(db_content: models.Content, target: ExtensionManifest, extension_path: Path) -> dispatch.Content:
    return dispatch.Content(
        name=db_content.name,
        content_type=db_content.content_type,
        path=extension_path / db_content.name,
        location=db_content.location,
        extension_id=target.id,
        extension_name=target.name,
        extension_version=target.version,
    )


async def _install(
    db: AsyncSession, db_content: models.Content, target: ExtensionManifest, extension_path: Path
) -> None:
    await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.INSTALLING)
    try:
        result = await dispatch.dispatcher.install_content(_content(db_content, target, extension_path))
    except Exception:
        await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.INSTALLATION_FAILED)
        raise
    await crud.update_content(
        db,
        content_id=db_content.id,
        status=models.ContentStatus.INSTALLED,
        location=result.location,
        applied_version=target.version,
    )


async def _update(
    db: AsyncSession, db_content: models.Content, target: ExtensionManifest, extension_path: Path
) -> None:
    await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.UPDATING)
    try:
        result = await dispatch.dispatcher.update_content(_content(db_content, target, extension_path))
    except Exception:
        await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.UPDATE_FAILED)
        raise
    await crud.update_content(
        db,
        content_id=db_content.id,
        status=models.ContentStatus.INSTALLED,
        location=result.location,
        applied_version=target.version,
    )


async def _uninstall(db: AsyncSession, db_content: models.Content) -> None:
    await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.UNINSTALLING)
    try:
        await dispatch.dispatcher.uninstall_content(
            dispatch.Content(name=db_content.name, content_type=db_content.content_type, location=db_content.location)
        )
    except Exception:
        await crud.update_content(db, content_id=db_content.id, status=models.ContentStatus.UNINSTALLATION_FAILED)
        raise
    await crud.delete_content(db, content_id=db_content.id)
