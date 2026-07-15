import base64
import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from v1.services import encryption
from v1.services.database import crud, database
from v1.services.database import exceptions as db_exceptions
from v1.services.oci.service import ociService

from ..dependencies import get_oci_service_for_repository
from . import schemas

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=schemas.Repository)
async def create_extension_repository(
    extension_repository: schemas.PostRepositoryRequest,
    response: Response,
    db: AsyncSession = Depends(database.get_async_db),
):
    encrypted_auth = encryption.encrypt(
        extension_repository.username, extension_repository.password.get_secret_value()
    )
    try:
        db_registered_repository = await crud.create_registered_repository(
            db,
            name=extension_repository.name,
            description=extension_repository.description,
            repository_url=extension_repository.repository_url,
            authentication=encrypted_auth,
        )
    except db_exceptions.RepositoryExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A repository with the name {extension_repository.name} already exists with id {e.repository_id}",
        )
    response.headers["Location"] = f"/repositories/{db_registered_repository.id}"

    return db_registered_repository


@router.get("", response_model=list[schemas.Repository])
async def get_registered_repository(
    name: Optional[str] = None,
    repository_id: Optional[UUID] = None,
    db: AsyncSession = Depends(database.get_async_db),
):
    return await crud.list_registered_repositories(
        db, name=name, repository_id=repository_id
    )


@router.get("/{repository_id}", response_model=schemas.Repository)
async def get_registered_repository_by_id(
    repository_id: UUID, db: AsyncSession = Depends(database.get_async_db)
):
    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    return repository


@router.put(
    "/{repository_id}",
    status_code=status.HTTP_200_OK,
    response_model=schemas.Repository,
)
async def update_repository(
    repository_id: UUID,
    response: Response,
    update_repository: schemas.PutRepositoryRequest,
    db: AsyncSession = Depends(database.get_async_db),
):
    encrypted_auth = None
    if update_repository.username is not None and update_repository.password is not None:
        encrypted_auth = encryption.encrypt(
            update_repository.username,
            update_repository.password.get_secret_value(),
        )

    try:
        db_registered_repository = await crud.update_registered_repository(
            db,
            id=repository_id,
            name=update_repository.name,
            description=update_repository.description,
            repository_url=update_repository.repository_url,
            authentication=encrypted_auth,
        )

    except NoResultFound:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    response.headers["Location"] = f"/repository/{db_registered_repository.id}"
    return db_registered_repository


@router.delete("/{repository_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repository(
    repository_id: UUID, db: AsyncSession = Depends(database.get_async_db)
):
    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    await crud.delete_registered_repository(db, repository_id)


########## Get Information about Extensions in Repository ##########


@router.get("/{repository_id}/extensions", response_model=list[str])
async def get_extensions(
    oci: ociService = Depends(get_oci_service_for_repository),
):
    return await oci.get_extensions_for_repository()


@router.get(
    "/{repository_id}/extensionManifests",
    response_model=list[schemas.ExtensionsManifestsResponse],
)
async def get_extension_manifests(
    repository_id: UUID,
    tags: str | None = None,
    oci: ociService = Depends(get_oci_service_for_repository),
):

    extensions_manifests = await oci.get_extension_manifests(
        tags=set(tags.split(",")) if tags else None
    )

    return [
        schemas.ExtensionsManifestsResponse(
            tag=tag, manifest=manifest, repository_id=repository_id
        )
        for tag, manifest in extensions_manifests.items()
    ]
