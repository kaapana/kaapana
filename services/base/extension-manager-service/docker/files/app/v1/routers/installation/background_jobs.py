import asyncio
import json
import shutil
from pathlib import Path
from uuid import UUID

from v1.services import dispatch
from v1.services.database import crud, database, models
from v1.services.logger import get_logger
from v1.services.oci.service import ociService

logger = get_logger(__name__)


async def install_extension_background_task(
    extension_id: UUID,
):
    logger.info(f"Installing extension with id {extension_id} in background task")

    async with database.async_session() as db:
        #### PULLING EXTENSION ####
        db_extension = await crud.update_extension(
            db, extension_id=extension_id, status=models.ExtensionStatus.PULLING
        )
        db_repository = await crud.get_registered_repository(
            db, db_extension.repository_id
        )
        if not db_repository:
            logger.warning("Repository not found. Cancel installation.")
            return

        async with ociService(
            db_repository.repository_url,
            db_repository.authentication,
        ) as oci:
            try:
                extension_path = await oci.pull_extension(tag=db_extension.tag)
            except Exception as e:
                await crud.update_extension(
                    db,
                    extension_id=extension_id,
                    status=models.ExtensionStatus.PULLING_FAILED,
                )
                raise e

            #### INSTALLING CONTENT ####
            db_extension = await crud.update_extension(
                db, extension_id=extension_id, status=models.ExtensionStatus.INSTALLING
            )
            try:
                with open(extension_path / "extension_manifest.json") as f:
                    extension_manifest = json.load(f)
                    assert extension_manifest == db_extension.manifest

                content_exceptions = []

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
                            )
                        )

                        await crud.update_content(
                            db,
                            content_id=content.id,
                            status=models.ContentStatus.INSTALLED,
                            location=result.location,
                        )
                    except Exception as e:
                        await crud.update_content(
                            db,
                            content_id=content.id,
                            status=models.ContentStatus.INSTALLATION_FAILED,
                        )
                        content_exceptions.append(e)

            except Exception as e:
                await crud.update_extension(
                    db,
                    extension_id=extension_id,
                    status=models.ExtensionStatus.INSTALLATION_FAILED,
                )
                raise e

            if content_exceptions:
                await crud.update_extension(
                    db,
                    extension_id=extension_id,
                    status=models.ExtensionStatus.INSTALLATION_FAILED,
                )
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
    logger.info(f"Unnstalling extension with id {extension_id} in background task")

    async with database.async_session() as db:
        db_extension = await crud.get_extension(db, extension_id=extension_id)
        if not db_extension:
            logger.warning("Extension not found. Cancel uninstallation!")
            return

        #### UNINSTALLING CONTENT ####
        try:
            content_exceptions = []

            for content in db_extension.contents:
                #### UNINSTALLING CONTENT ####
                if content.status == models.ContentStatus.UNINSTALLED:
                    logger.info(
                        f"Content with id {content.id} and name {content.name} is already in status {content.status}"
                    )
                    continue
                if content.status == models.ContentStatus.PENDING:
                    logger.info(
                        f"Content with id {content.id} and name {content.name} still in status {content.status}"
                    )
                    continue

                content = await crud.update_content(
                    db,
                    content_id=content.id,
                    status=models.ContentStatus.UNINSTALLING,
                )
                try:
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
                    await crud.update_content(
                        db,
                        content_id=content.id,
                        status=models.ContentStatus.UNINSTALLATION_FAILED,
                    )
                    content_exceptions.append(e)

        except Exception as e:
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.UNINSTALLING_FAILED,
            )
            raise e

        if content_exceptions:
            await crud.update_extension(
                db,
                extension_id=extension_id,
                status=models.ExtensionStatus.UNINSTALLING_FAILED,
            )
            raise ExceptionGroup(
                "One or more content installations failed",
                content_exceptions,
            )

        await crud.update_extension(
            db, extension_id=extension_id, status=models.ExtensionStatus.UNINSTALLED
        )

        await asyncio.sleep(30)
        await crud.delete_extension(db, extension_id=extension_id)
