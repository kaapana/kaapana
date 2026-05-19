from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
import base64, json

from v1.services.database import crud, database
from v1.services.database import exceptions as db_exceptions
from v1.routers.repository import schemas

from v1.services.oci.service import ociService
from v1.routers.dependencies import get_oci_service_for_repository

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
)
async def create_extension_repository(
    extension_repository: schemas.PostRepositoryRequest,
    response: Response,
    db: AsyncSession = Depends(database.get_async_db),
):
    authentication = {
        "username": extension_repository.username,
        "password": extension_repository.password,
    }

    encoded_auth = base64.b64encode(json.dumps(authentication).encode()).decode()
    try:
        db_registered_repository = await crud.create_registered_repository(
            db,
            name=extension_repository.name,
            description=extension_repository.description,
            repository_url=extension_repository.repository_url,
            authentication=encoded_auth,
        )
    except db_exceptions.RepositoryExistsException as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A repository with the name {extension_repository.name} already exists with id {e.repository_id}",
        )
    response.headers["Location"] = f"/repositories/{db_registered_repository.id}"
    response.status_code = status.HTTP_201_CREATED

    return response


@router.get("", response_model=list[schemas.Repository])
async def get_registered_repository(
    name: Optional[str] = None,
    repository_id: Optional[UUID] = None,
    db: AsyncSession = Depends(database.get_async_db),
):
    repositories = await crud.list_registered_repositories(
        db, name=name, repository_id=repository_id
    )
    return repositories


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


@router.put("/{repository_id}")
async def update_repository(
    repository_id: UUID,
    response: Response,
    update_repository: schemas.PutRepositoryRequest,
    db: AsyncSession = Depends(database.get_async_db),
):

    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )

    authentication = {
        "username": update_repository.username,
        "password": update_repository.password,
    }

    encoded_auth = base64.b64encode(json.dumps(authentication).encode()).decode()

    db_registered_repository = await crud.update_registered_repository(
        db,
        id=repository_id,
        name=update_repository.name,
        description=update_repository.description,
        repository_url=update_repository.repository_url,
        authentication=encoded_auth,
    )

    response.headers["Location"] = f"/repository/{db_registered_repository.id}"
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.delete("/{repository_id}")
async def delete_repository(
    repository_id: UUID, db: AsyncSession = Depends(database.get_async_db)
):
    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    await crud.delete_registered_repository(db, repository_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


########## Get Information about Extensions in Repository ##########


@router.get("/{repository_id}/extensions", response_model=list[str])
async def get_extensions(
    repository_id: UUID,
    oci: ociService = Depends(get_oci_service_for_repository),
    db: AsyncSession = Depends(database.get_async_db),
):
    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    extensions = await oci.get_extensions_for_repository()

    return extensions


@router.get(
    "/{repository_id}/extensionManifests",
    response_model=list[schemas.ExtensionsManifestsResponse],
)
async def get_extension_manifests(
    repository_id: UUID,
    tags: str | None = None,
    oci: ociService = Depends(get_oci_service_for_repository),
    db: AsyncSession = Depends(database.get_async_db),
):

    repository = await crud.get_registered_repository(db, repository_id)
    if not repository:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Repository not found"
        )
    extensions_manifests = await oci.get_extension_manifests(
        tags=tags.split(",") if tags else None
    )

    return [
        schemas.ExtensionsManifestsResponse(
            tag=tag, manifest=manifest, repository_id=repository_id
        )
        for tag, manifest in extensions_manifests.items()
    ]
