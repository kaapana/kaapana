import asyncio
import json
import shutil
from pathlib import Path
from uuid import UUID

from sqlalchemy.exc import NoResultFound
from v1.services import dispatch
from v1.services.database import crud, database, models
from v1.services.database.exceptions import NotSupportedExtensionStateTransition
from v1.services.logger import get_logger
from v1.services.oci.models import ExtensionManifest
from v1.services.oci.service import ociService

logger = get_logger(__name__)


class ExtensionFilesNotFound(Exception):
    pass


def _reason(error: BaseException) -> str:
    return str(error) or type(error).__name__


async def _fetch_extension_files(db, db_extension: models.Extension) -> Path:
    db_repository = await crud.get_registered_repository(db, db_extension.repository_id)
    if not db_repository:
        raise ExtensionFilesNotFound("The repository of this extension was removed.")

    async with ociService(
        db_repository.repository_url,
        db_repository.authentication,
    ) as oci:
        return await oci.pull_extension(tag=db_extension.tag)


async def install_extension_background_task(
    extension_id: UUID,
):
    logger.info(f"Installing extension with id {extension_id} in background task")
    async with database.async_session() as db:
        #### PULLING EXTENSION ####
        try:
            db_extension = await crud.update_extension(
                db, extension_id=extension_id, status=models.ExtensionStatus.PULLING
            )
        except NotSupportedExtensionStateTransition:
            logger.warning(f"Cannot change status of extension with id {extension_id} to pulling. Cancel installation!")
            return
        except NoResultFound:
            logger.warning(f"Extension with id {extension_id} not found. Cancel installation.")
            return

        try:
            extension_path = await _fetch_extension_files(db, db_extension)
        except ExtensionFilesNotFound as e:
            logger.warning("Cannot install extension '%s': %s", db_extension.tag, e)
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.PULLING_FAILED,
                reason=str(e),
            )
            return
        except Exception as e:
            logger.error("Failed to pull extension '%s': %s", db_extension.tag, e, exc_info=True)
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.PULLING_FAILED,
                reason=f"Download failed: {_reason(e)}",
            )
            raise

        #### INSTALLING CONTENT ####
        db_extension = await crud.update_extension(
            db, extension_id=extension_id, status=models.ExtensionStatus.INSTALLING
        )
        try:
            with open(extension_path / "extension_manifest.json") as f:
                extension_manifest = json.load(f)
                assert ExtensionManifest(**extension_manifest).model_dump(mode="json") == db_extension.manifest

            content_exceptions = []
            content_errors = []

            for content in db_extension.contents:
                #### INSTALLING CONTENT ####
                if content.status == models.ContentStatus.INSTALLED:
                    logger.info(
                        f"Content with id {content.id} and name {content.name} is already in status {content.status}"
                    )
                    continue
                content = await crud.update_content(
                    db,
                    content_id=content.id,
                    status=models.ContentStatus.INSTALLING,
                )
                try:
                    result = await dispatch.dispatcher.install_content(
                        dispatch.Content(
                            name=content.name,
                            content_type=content.content_type,
                            path=extension_path / content.name,
                            extension_id=extension_manifest["id"],
                            extension_name=extension_manifest["name"],
                            extension_version=extension_manifest["version"],
                        )
                    )

                    await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.INSTALLED,
                        location=result.location,
                    )
                except Exception as e:
                    logger.error("Failed to install content '%s': %s", content.name, e, exc_info=True)
                    await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.INSTALLATION_FAILED,
                    )
                    content_exceptions.append(e)
                    content_errors.append(f"{content.name}: {_reason(e)}")

        except Exception as e:
            logger.error(
                "Unexpected error during installation of extension '%s': %s", db_extension.tag, e, exc_info=True
            )
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.INSTALLATION_FAILED,
                reason=f"Installation failed: {_reason(e)}",
            )
            shutil.rmtree(Path(extension_path))
            raise

        if content_exceptions:
            logger.error(
                "%d content(s) failed to install for extension '%s'",
                len(content_exceptions),
                db_extension.tag,
            )
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.INSTALLATION_FAILED,
                reason="; ".join(content_errors),
            )
            shutil.rmtree(Path(extension_path))
            raise ExceptionGroup(
                "One or more content installations failed",
                content_exceptions,
            )

        db_extension = await crud.update_extension(
            db, extension_id=extension_id, status=models.ExtensionStatus.INSTALLED
        )

    shutil.rmtree(Path(extension_path))


async def uninstall_extension_background_task(
    extension_id: UUID,
):
    logger.info(f"Uninstalling extension with id {extension_id} in background task")

    async with database.async_session() as db:
        db_extension = await crud.get_extension(db, extension_id=extension_id)
        if not db_extension:
            logger.warning("Extension not found. Cancel uninstallation!")
            return

        #### UNINSTALLING CONTENT ####
        try:
            content_exceptions = []
            content_errors = []

            for content in db_extension.contents:
                #### UNINSTALLING CONTENT ####
                if content.status == models.ContentStatus.UNINSTALLED:
                    logger.info(
                        f"Content with id {content.id} and name {content.name} is already in status {content.status}"
                    )
                    continue

                try:
                    content = await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.UNINSTALLING,
                    )
                    await dispatch.dispatcher.uninstall_content(
                        dispatch.Content(
                            name=content.name,
                            content_type=content.content_type,
                            location=content.location,
                        )
                    )

                    await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.UNINSTALLED,
                    )
                except Exception as e:
                    logger.error("Failed to uninstall content '%s': %s", content.name, e, exc_info=True)
                    await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.UNINSTALLATION_FAILED,
                    )
                    content_exceptions.append(e)
                    content_errors.append(f"{content.name}: {_reason(e)}")

        except Exception as e:
            logger.error(
                "Unexpected error during uninstallation of extension id=%s: %s", extension_id, e, exc_info=True
            )
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.UNINSTALLING_FAILED,
                reason=f"Uninstallation failed: {_reason(e)}",
            )
            raise

        if content_exceptions:
            logger.error(
                "%d content(s) failed to uninstall for extension id=%s",
                len(content_exceptions),
                extension_id,
            )
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.UNINSTALLING_FAILED,
                reason="; ".join(content_errors),
            )
            raise ExceptionGroup(
                "One or more content uninstallations failed",
                content_exceptions,
            )

        await crud.update_extension(db, extension_id=extension_id, status=models.ExtensionStatus.UNINSTALLED)

    await asyncio.sleep(30)
    async with database.async_session() as db2:
        await crud.delete_extension(db2, extension_id=extension_id)
