import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from sqlalchemy.exc import NoResultFound
from v1.services import dispatch
from v1.services.database import crud, database
from v1.services.database.exceptions import (
    LockedExtensionException,
    NotSupportedExtensionStateTransition,
)
from v1.services.oci.exceptions import ExtensionNotFoundException
from v1.services.oci.service import ociService

from ..dependencies import get_oci_service_for_repository
from . import schemas
from .background_jobs import (
    install_extension_background_task,
    uninstall_extension_background_task,
)

router = APIRouter(prefix="/extensions", tags=["extensions"])


@router.post(
    "/install",
    response_model=schemas.InstalledExtension,
    status_code=status.HTTP_201_CREATED,
)
async def install_extension(
    repository_id: UUID,
    tag: str,
    response: Response,
    background_tasks: BackgroundTasks,
    oci: ociService = Depends(get_oci_service_for_repository),
    db=Depends(database.get_async_db),
):

    try:
        extension_manifest = await oci.get_extension_manifest(tag=tag)
    except ExtensionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Extension with tag {tag} not found in {oci.repository_url}",
        ) from e

    for content in extension_manifest.contents:
        if not dispatch.dispatcher.find_installer(
            dispatch.Content(name=content.name, content_type=content.contentType)
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No installer found for content type {content.contentType}",
            )

    if db_extensions := await crud.list_extensions(
        db, repository_id=repository_id, tag=tag
    ):
        ### RETRY INSTALLATION ###
        db_extension = db_extensions[0]
        try:
            await crud.update_extension(
                db,
                extension_id=db_extension.id,
                status=crud.ExtensionStatus.PENDING,
            )
        except NotSupportedExtensionStateTransition as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because the extension exists and is in an non-terminal state.",
            ) from e
        except LockedExtensionException as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because an extension with the same tag is currently being installed or is already installed",
            ) from e
    else:
        ### INSTALL FOR THE FIRST TIME ###
        db_extension = await crud.create_extension(
            session=db,
            repository_id=repository_id,
            tag=tag,
            manifest=extension_manifest.model_dump(mode="json"),
        )

        for content in extension_manifest.contents:
            await crud.create_content(
                db,
                extension_id=db_extension.id,
                content_type=content.contentType,
                name=content.name,
            )

    background_tasks.add_task(install_extension_background_task, db_extension.id)

    response.headers["Location"] = f"/extensions/{db_extension.id}"
    return await crud.get_extension(db, extension_id=db_extension.id)


@router.get("", response_model=list[schemas.InstalledExtension])
async def get_extensions(
    tag: Optional[str] = None,
    repository_id: Optional[UUID] = None,
    db=Depends(database.get_async_db),
):
    return await crud.list_extensions(db, repository_id=repository_id, tag=tag)


@router.get(
    "/{extension_id}",
    response_model=schemas.InstalledExtension,
    status_code=status.HTTP_200_OK,
)
async def get_extension(extension_id: UUID, db=Depends(database.get_async_db)):
    db_extension = await crud.get_extension(db, extension_id=extension_id)
    if not db_extension:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found"
        )
    return db_extension


@router.post("/{extension_id}/uninstall", status_code=status.HTTP_202_ACCEPTED)
async def uninstall_extension(
    extension_id: UUID,
    background_tasks: BackgroundTasks,
    db=Depends(database.get_async_db),
):
    try:
        db_extension = await crud.update_extension(
            db, extension_id=extension_id, status=crud.ExtensionStatus.UNINSTALLING
        )
    except NotSupportedExtensionStateTransition as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot uninstall the extension with id {extension_id}, because the extension exists in an un-terminated status.",
        ) from e
    except LockedExtensionException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot uninstall the extension with id {extension_id}, because the extension is already processed",
        ) from e
    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found"
        )
    background_tasks.add_task(uninstall_extension_background_task, db_extension.id)
