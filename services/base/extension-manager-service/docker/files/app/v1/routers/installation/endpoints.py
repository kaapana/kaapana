import shutil
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError, NoResultFound
from v1.services import dispatch, upload
from v1.services.database import crud, database
from v1.services.database.exceptions import (
    LockedExtensionException,
    NotSupportedExtensionStateTransition,
)
from v1.services.dispatch.exceptions import ContentError
from v1.services.oci.exceptions import ExtensionNotFoundException
from v1.services.oci.models import ExtensionManifest
from v1.services.oci.service import ociService

from ..dependencies import get_oci_service_for_repository, get_upload_repository_service
from ..repository import schemas as repository_schemas
from . import schemas
from .background_jobs import (
    install_extension_background_task,
    uninstall_extension_background_task,
)

router = APIRouter(prefix="/extensions", tags=["extensions"])


def _ensure_installers_exist(extension_manifest: ExtensionManifest) -> None:
    for content in extension_manifest.contents:
        try:
            dispatch.dispatcher.find_installer(dispatch.Content(name=content.name, content_type=content.contentType))
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No installer found for content type {content.contentType}",
            ) from e


async def _ensure_not_in_other_repository(db, repository_id: UUID, tag: str) -> None:
    for db_extension in await crud.list_extensions(db, tag=tag):
        if db_extension.repository_id == repository_id or db_extension.status == crud.ExtensionStatus.UNINSTALLED:
            continue
        db_repository = await crud.get_registered_repository(db, db_extension.repository_id)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"The extension {db_extension.manifest['name']} {db_extension.manifest['version']} "
                f"is already installed from the repository {db_repository.name}. Uninstall it first."
            ),
        )


async def _create_or_reset_extension(db, repository_id: UUID, tag: str, extension_manifest: ExtensionManifest):
    db_extensions = await crud.list_extensions(db, repository_id=repository_id, tag=tag)
    if db_extensions:
        db_extension = db_extensions[0]
        try:
            return await crud.update_extension(db, extension_id=db_extension.id, status=crud.ExtensionStatus.PENDING)
        except NotSupportedExtensionStateTransition as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because the extension exists and is in status {db_extension.status}",
            ) from e
        except LockedExtensionException as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because an extension with the same tag is currently being processed",
            ) from e

    try:
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
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot install extension with tag {tag} from repository {repository_id} because an extension with the same tag is currently being processed",
        ) from e
    return db_extension


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

    _ensure_installers_exist(extension_manifest)
    await _ensure_not_in_other_repository(db, repository_id, tag)
    db_extension = await _create_or_reset_extension(db, repository_id, tag, extension_manifest)

    background_tasks.add_task(install_extension_background_task, db_extension.id)

    response.headers["Location"] = f"/extensions/{db_extension.id}"
    return await crud.get_extension(db, extension_id=db_extension.id)


UPLOAD_READING_STATUSES = {crud.ExtensionStatus.PENDING, crud.ExtensionStatus.PULLING}


async def _upload_installations(db, tag: str):
    return await crud.list_extensions(db, repository_id=upload.UPLOAD_REPOSITORY_ID, tag=tag)


def _ensure_not_being_pulled(db_extensions, tag: str) -> None:
    if any(db_extension.status in UPLOAD_READING_STATUSES for db_extension in db_extensions):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"The extension with tag {tag} is being installed from the Upload repository. Try again later.",
        )


@router.post(
    "/upload",
    response_model=repository_schemas.ExtensionsManifestsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_extension(
    file: UploadFile,
    response: Response,
    upload_repository: ociService = Depends(get_upload_repository_service),
    db=Depends(database.get_async_db),
):
    filename = file.filename or ""
    if not filename.endswith(upload.ARCHIVE_SUFFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {upload.ARCHIVE_SUFFIX} archives built with extensionctl can be uploaded.",
        )

    staging_dir = upload.create_staging_dir()
    try:
        try:
            archive = await upload.receive_archive(file, staging_dir)
        except upload.UploadTooLargeException as e:
            raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(e)) from e

        extracted_dir = staging_dir / "extension"
        try:
            extension_manifest = upload.extract_archive(archive, extracted_dir)
        except upload.InvalidArchiveException as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

        _ensure_installers_exist(extension_manifest)
        for content in extension_manifest.contents:
            try:
                dispatch.dispatcher.validate_content(
                    dispatch.Content(
                        name=content.name, content_type=content.contentType, path=extracted_dir / content.name
                    )
                )
            except ContentError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"The content {content.name} is invalid: {e}",
                ) from e

        tag = upload.extension_tag(extension_manifest)
        db_extensions = await _upload_installations(db, tag)
        _ensure_not_being_pulled(db_extensions, tag)
        if any(
            db_extension.status != crud.ExtensionStatus.UNINSTALLED
            and db_extension.manifest != extension_manifest.model_dump(mode="json")
            for db_extension in db_extensions
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"The extension {extension_manifest.name} {extension_manifest.version} is installed "
                    "with a different manifest. Uninstall it first."
                ),
            )
        await upload_repository.push_extension(archive)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    response.headers["Location"] = f"/repositories/{upload.UPLOAD_REPOSITORY_ID}/extensionManifests?tags={tag}"
    return repository_schemas.ExtensionsManifestsResponse(
        repository_id=upload.UPLOAD_REPOSITORY_ID, tag=tag, manifest=extension_manifest
    )


@router.delete("/uploads/{tag}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_uploaded_extension(
    tag: str,
    upload_repository: ociService = Depends(get_upload_repository_service),
    db=Depends(database.get_async_db),
):
    _ensure_not_being_pulled(await _upload_installations(db, tag), tag)
    try:
        await upload_repository.delete_extension(tag)
    except ExtensionNotFoundException as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"The extension with tag {tag} was not uploaded.",
        ) from e


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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found")
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Extension not found")
    background_tasks.add_task(uninstall_extension_background_task, db_extension.id)
