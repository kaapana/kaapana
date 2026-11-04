import shutil
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Response, UploadFile, status
from sqlalchemy.exc import IntegrityError, NoResultFound
from v1.services import dispatch, upload
from v1.services.database import crud, database, models
from v1.services.database.exceptions import (
    LockedExtensionException,
    NotSupportedExtensionStateTransition,
)
from v1.services.dispatch.exceptions import ContentError
from v1.services.oci.exceptions import ExtensionNotFoundException
from v1.services.oci.models import ExtensionManifest
from v1.services.oci.service import ociService

from ..dependencies import get_oci_service_for_repository
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

    except IntegrityError:
        await db.rollback()
        db_extensions = await crud.list_extensions(db, repository_id=repository_id, tag=tag)
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
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because the extension exists and is in status {db_extension.status}",
            ) from e
        except LockedExtensionException as e:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot install extension with tag {tag} from repository {repository_id} because an extension with the same tag is currently being processed",
            ) from e

    background_tasks.add_task(install_extension_background_task, db_extension.id)

    response.headers["Location"] = f"/extensions/{db_extension.id}"
    return await crud.get_extension(db, extension_id=db_extension.id)


@router.post(
    "/upload",
    response_model=schemas.InstalledExtension,
    status_code=status.HTTP_201_CREATED,
)
async def upload_extension(
    file: UploadFile,
    response: Response,
    background_tasks: BackgroundTasks,
    uploaded_by: Annotated[Optional[str], Header(alias="X-Forwarded-Preferred-Username")] = None,
    db=Depends(database.get_async_db),
):
    filename = file.filename or ""
    if not filename.endswith(upload.ARCHIVE_SUFFIX):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only {upload.ARCHIVE_SUFFIX} archives built with extensionctl can be installed.",
        )
    if len(filename) > upload.MAX_NAME_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The file name is longer than {upload.MAX_NAME_LENGTH} characters.",
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

        db_extensions = await crud.list_extensions(db, origin=models.ExtensionOrigin.UPLOAD, tag=tag)
        if db_extensions:
            db_extension = db_extensions[0]
            try:
                await crud.update_extension(db, extension_id=db_extension.id, status=crud.ExtensionStatus.PENDING)
            except (NotSupportedExtensionStateTransition, LockedExtensionException) as e:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Cannot install {filename} because the extension {tag} exists and is in status {db_extension.status}",
                ) from e
            await crud.update_extension_upload(
                db, extension_id=db_extension.id, uploaded_by=uploaded_by, uploaded_filename=filename
            )
        else:
            db_extension = await crud.create_extension(
                session=db,
                repository_id=None,
                tag=tag,
                manifest=extension_manifest.model_dump(mode="json"),
                origin=models.ExtensionOrigin.UPLOAD,
                uploaded_by=uploaded_by,
                uploaded_filename=filename,
            )
            for content in extension_manifest.contents:
                await crud.create_content(
                    db,
                    extension_id=db_extension.id,
                    content_type=content.contentType,
                    name=content.name,
                )

        upload.store_extension(extracted_dir, tag)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

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
