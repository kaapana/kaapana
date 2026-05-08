from v1.services.database.database import AsyncSession
from v1.services.database import crud, models

from v1.services.oci.service import ociService
from v1.services import dispatch
import json


async def install_extension_background_task(
    extension_id: str,
    db: AsyncSession,
    oci: ociService,
):
    print(f"Installing extension with id {extension_id} in background task")

    #### PULLING EXTENSION ####
    db_extension = await crud.update_extension(
        db, extension_id=extension_id, status=models.ExtensionStatus.PULLING
    )
    try:
        extension_path = await oci.pull_extension(tag=db_extension.tag)
    except Exception as e:
        await crud.update_extension(
            db, extension_id=extension_id, status=models.ExtensionStatus.PULLING_FAILED
        )
        raise e

    #### INSTALLING EXTENSION ####

    db_extension = await crud.update_extension(
        db, extension_id=extension_id, status=models.ExtensionStatus.INSTALLING
    )
    try:
        with open(extension_path / "manifest.json") as f:
            extension_manifest = json.load(f)
            assert extension_manifest == json.loads(db_extension.manifest)

        for content in db_extension.contents:
            #### INSTALLING CONTENT ####
            try:
                result = await dispatch.Installer.install_content(
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
                    location=result.message,
                )
            except Exception as e:
                await crud.update_content(
                    db,
                    content_id=content.id,
                    status=models.ContentStatus.INSTALLATION_FAILED,
                )
                raise e

    except AssertionError as e:
        await crud.update_extension(
            db,
            extension_id=extension_id,
            status=models.ExtensionStatus.INSTALLATION_FAILED,
        )
        raise e

    except Exception as e:
        await crud.update_extension(
            db,
            extension_id=extension_id,
            status=models.ExtensionStatus.INSTALLATION_FAILED,
        )
        raise e

    await crud.update_extension(
        db, extension_id=extension_id, status=models.ExtensionStatus.INSTALLED
    )
