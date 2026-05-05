from fastapi import Depends
from v1.services.database.database import get_async_db, AsyncSession
from v1.services.database import crud

from v1.services.oci.service import ociService
from v1.services.dispatch import Extension, Installer, Discovery

from v1.routers.dependencies import get_oci_service_for_repository


async def install_extension_background_task(
    extension_id: str,
    db: AsyncSession = Depends(get_async_db),
    oci: ociService = Depends(get_oci_service_for_repository),
):
    print(f"Installing extension with id {extension_id} in background task")

    #### PULLING EXTENSION ####
    await crud.update_extension(db, extension_id=extension_id, status="pulling")
    try:
        extension_path = await oci.pull_extension(tag=extension_id)
    except Exception as e:
        await crud.update_extension(
            db, extension_id=extension_id, status="pulling_failed"
        )
        raise e

    #### INSTALLING EXTENSION ####
    await crud.update_extension(db, extension_id=extension_id, status="installing")
    try:
        extension = Discovery.discover(extension_path=extension_path)
        await Installer.install(extension)

    except Exception as e:
        await crud.update_extension(
            db, extension_id=extension_id, status="installing_failed"
        )
        raise e

    await crud.update_extension(db, extension_id=extension_id, status="installed")
