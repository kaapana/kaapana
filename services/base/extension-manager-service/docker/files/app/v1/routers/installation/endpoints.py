from fastapi import APIRouter, Depends, HTTPException, status, Response, BackgroundTasks
from uuid import UUID
from typing import Optional
from v1.routers.dependencies import get_oci_service_for_repository
from v1.routers.installation.background_jobs import install_extension_background_task


from v1.services.database import crud, database

from v1.services.oci.service import ociService
from v1.services.oci.exceptions import ExtensionNotFoundException

from v1.routers.installation import schemas

router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.post("/install")
async def install_extension(
    repository_id: UUID,
    tag: str,
    response: Response,
    background_tasks: BackgroundTasks,
    oci: ociService = Depends(get_oci_service_for_repository),
    db=Depends(database.get_async_db),
):
    try:
        extension_manifests = await oci.get_extension_manifest(tag=tag)
    except ExtensionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extension with tag {tag} not found in {oci.repository_url}",
        ) from e

    db_extension = await crud.create_extension(
        session=db,
        repository_id=repository_id,
        tag=tag,
        manifest=extension_manifests["manifest"],
    )

    background_tasks.add_task(
        install_extension_background_task, db_extension.id, db, oci
    )

    response.headers["Location"] = f"/extensions/{db_extension.id}"
    response.status_code = status.HTTP_201_CREATED
    return response


@router.get("", response_model=list[schemas.InstalledExtension])
async def get_extensions(
    tag: Optional[str] = None,
    repository_id: Optional[UUID] = None,
    db=Depends(database.get_async_db),
):
    extensions = await crud.list_extensions(db, repository_id=repository_id, tag=tag)

    return extensions


@router.get("/{extension_id}", response_model=schemas.InstalledExtension)
async def get_extension_status(extension_id: UUID, db=Depends(database.get_async_db)):
    return await crud.get_extension(db, extension_id=extension_id)


@router.post("/{extension_id}/uninstall")
async def uninstall_extension(
    extension_id: UUID,
    response: Response,
    oci=Depends(get_oci_service_for_repository),
):
    pass
