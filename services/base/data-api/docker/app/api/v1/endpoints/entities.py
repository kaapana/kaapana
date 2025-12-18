from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataEntityORM
from app.db.session import AsyncSessionLocal, get_async_db
from app.models.domain import DataEntity, StorageCoordinate
from app.models.events import EventAction
from app.services.entity_repository import (
    entities_from_orms,
    entity_to_orm,
    fetch_entity_orm,
    fetch_entity_page,
    resolve_entity_cursor,
    storage_to_orm,
)
from .helpers import (
    broadcast_entity_event,
    cleanup_entity_artifacts,
    commit_and_return_entity,
    require_entity,
    require_entity_response,
)

router = APIRouter(prefix="/entities", tags=["entities"])


class EntityListResponse(BaseModel):
    items: list[UUID]
    next_cursor: UUID | None = Field(
        None,
        description="Pass this cursor to fetch the next page of IDs",
    )


class EntityRecordPage(BaseModel):
    items: list[DataEntity]
    next_cursor: UUID | None = Field(
        None,
        description="Pass this cursor to fetch the next page of entity records",
    )


@router.post("", response_model=DataEntity, summary="Create or replace a data entity")
async def create_entity(
    entity: DataEntity, db: AsyncSession = Depends(get_async_db)
) -> DataEntity:
    existing = await fetch_entity_orm(db, entity.id)
    if existing is not None:
        await db.delete(existing)
        await db.flush()

    db.add(entity_to_orm(entity))
    result = await commit_and_return_entity(db, entity.id)
    action = EventAction.UPDATED if existing else EventAction.CREATED
    await broadcast_entity_event(action, result)
    return result


@router.get(
    "", response_model=EntityListResponse, summary="List entity IDs with pagination"
)
async def list_entities(
    limit: int = Query(100, ge=1, le=10000),
    cursor: UUID | None = Query(
        None, description="Return entities created after the entity with this ID"
    ),
    db: AsyncSession = Depends(get_async_db),
) -> EntityListResponse:
    stmt = (
        select(DataEntityORM.id, DataEntityORM.created_at)
        .order_by(DataEntityORM.created_at, DataEntityORM.id)
        .limit(limit + 1)
    )
    if cursor:
        try:
            created_at, entity_id = await resolve_entity_cursor(db, cursor)
        except ValueError as exc:  # pragma: no cover - defensive
            raise HTTPException(status_code=400, detail="Invalid cursor") from exc
        stmt = stmt.where(
            tuple_(DataEntityORM.created_at, DataEntityORM.id)
            > tuple_(created_at, entity_id)
        )
    result = await db.execute(stmt)
    rows = result.all()
    has_more = len(rows) > limit
    page_rows = rows[:limit]
    items = [row[0] for row in page_rows]
    next_cursor = items[-1] if has_more and items else None
    return EntityListResponse(items=items, next_cursor=next_cursor)


@router.get(
    "/index/full",
    response_class=StreamingResponse,
    summary="Stream the full ordered list of entity IDs",
    description="Efficiently load large catalogs by streaming the entire ID index as JSON without cursor round-trips.",
)
async def stream_entity_index(
    db: AsyncSession = Depends(get_async_db),
) -> StreamingResponse:
    total_count_stmt = select(func.count(DataEntityORM.id))
    total_count_result = await db.execute(total_count_stmt)
    total_count = int(total_count_result.scalar() or 0)

    stmt = (
        select(DataEntityORM.id)
        .order_by(DataEntityORM.created_at, DataEntityORM.id)
        .execution_options(stream_results=True)
    )

    async def iterator() -> AsyncIterator[bytes]:
        yield b'{"total_count":' + str(total_count).encode() + b',"items":['
        first = True
        async with AsyncSessionLocal() as stream_session:
            result = await stream_session.stream(stmt)
            try:
                async for entity_id in result.scalars():
                    prefix = b"" if first else b","
                    first = False
                    yield prefix + f'"{entity_id}"'.encode()
            finally:
                await result.close()
        yield b'],"next_cursor":null}'

    return StreamingResponse(iterator(), media_type="application/json")


@router.get(
    "/records",
    response_model=EntityRecordPage,
    summary="List full entity records with pagination",
)
async def list_entity_records(
    limit: int = Query(50, ge=1, le=10000),
    cursor: UUID | None = Query(
        None, description="Return entities created after the entity with this ID"
    ),
    db: AsyncSession = Depends(get_async_db),
) -> EntityRecordPage:
    try:
        entity_orms = await fetch_entity_page(db, cursor=cursor, limit=limit)
    except ValueError as exc:  # pragma: no cover - defensive
        raise HTTPException(status_code=400, detail="Invalid cursor") from exc
    has_more = len(entity_orms) > limit
    page_orms = entity_orms[:limit]
    items = entities_from_orms(page_orms)
    next_cursor = items[-1].id if has_more and items else None
    return EntityRecordPage(items=items, next_cursor=next_cursor)


@router.get(
    "/{entity_id}", response_model=DataEntity, summary="Get a data entity by ID"
)
async def get_entity(
    entity_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> DataEntity:
    return await require_entity_response(db, entity_id)


@router.post(
    "/{entity_id}/storage-coordinates",
    response_model=DataEntity,
    summary="Add a storage coordinate to an entity",
)
async def add_storage_coordinate(
    entity_id: UUID,
    coord: StorageCoordinate,
    db: AsyncSession = Depends(get_async_db),
) -> DataEntity:
    entity = await require_entity(db, entity_id)
    entity.storage_coordinates.append(storage_to_orm(coord))
    updated = await commit_and_return_entity(db, entity_id)
    await broadcast_entity_event(EventAction.UPDATED, updated)
    return updated


@router.delete(
    "/{entity_id}/storage-coordinates",
    response_model=DataEntity,
    summary="Remove a storage coordinate from an entity by index",
)
async def remove_storage_coordinate(
    entity_id: UUID, index: int, db: AsyncSession = Depends(get_async_db)
) -> DataEntity:
    entity = await require_entity(db, entity_id)
    try:
        entity.storage_coordinates.pop(index)
    except IndexError as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=400, detail="Invalid storage coordinate index"
        ) from exc
    updated = await commit_and_return_entity(db, entity_id)
    await broadcast_entity_event(EventAction.UPDATED, updated)
    return updated


@router.delete("/{entity_id}", status_code=204, summary="Delete a data entity")
async def delete_entity(
    entity_id: UUID, db: AsyncSession = Depends(get_async_db)
) -> Response:
    entity = await require_entity(db, entity_id)
    await db.delete(entity)
    await db.commit()
    cleanup_entity_artifacts(entity_id)
    await broadcast_entity_event(EventAction.DELETED, entity_id)
    return Response(status_code=204)
