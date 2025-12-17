from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import MetadataEntryORM
from app.db.session import get_async_db
from app.models.domain import Artifact, DataEntity
from app.models.events import EventAction
from app.services.artifact_store import get_artifact_store
from app.services.entity_repository import artifact_to_orm
from .helpers import (
    broadcast_entity_event,
    commit_and_return_entity,
    get_metadata_schema,
    require_entity,
)

router = APIRouter(tags=["artifacts"])


@router.post(
    "/entities/{entity_id}/metadata/{key}/artifacts/{artifact_id}",
    response_model=DataEntity,
    summary="Upload an artifact for a metadata entry",
)
async def upload_artifact(
    entity_id: UUID,
    key: str,
    artifact_id: str,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
) -> DataEntity:
    entity = await require_entity(db, entity_id)

    metadata_entry = next((m for m in entity.metadata_entries if m.key == key), None)
    if metadata_entry is None:
        await get_metadata_schema(db, key)
        metadata_entry = MetadataEntryORM(key=key, data={})
        entity.metadata_entries.append(metadata_entry)

    existing_artifact = next(
        (a for a in metadata_entry.artifacts if a.artifact_id == artifact_id), None
    )
    if existing_artifact is not None:
        metadata_entry.artifacts.remove(existing_artifact)

    store = get_artifact_store()
    path = store.save(str(entity_id), key, artifact_id, file.file)

    artifact = Artifact(
        id=artifact_id,
        filename=file.filename,
        content_type=file.content_type,
        size_bytes=path.stat().st_size,
    )
    metadata_entry.artifacts.append(artifact_to_orm(artifact))

    updated = await commit_and_return_entity(db, entity_id)
    await broadcast_entity_event(EventAction.UPDATED, updated)
    return updated


@router.get(
    "/entities/{entity_id}/metadata/{key}/artifacts/{artifact_id}",
    summary="Download an artifact for a metadata entry",
)
async def download_artifact(
    entity_id: UUID,
    key: str,
    artifact_id: str,
    disposition: str = Query("attachment", regex="^(inline|attachment)$"),
    db: AsyncSession = Depends(get_async_db),
):
    entity = await require_entity(db, entity_id)

    metadata_entry = next((m for m in entity.metadata_entries if m.key == key), None)
    if metadata_entry is None:
        raise HTTPException(status_code=404, detail="Metadata entry not found")

    artifact = next(
        (a for a in metadata_entry.artifacts if a.artifact_id == artifact_id), None
    )
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found")

    store = get_artifact_store()
    fileobj = store.open(str(entity_id), key, artifact_id)

    dispo = "inline" if disposition == "inline" else "attachment"
    filename = artifact.filename or artifact.artifact_id

    return StreamingResponse(
        fileobj,
        media_type=artifact.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"{dispo}; filename={filename}",
        },
    )
