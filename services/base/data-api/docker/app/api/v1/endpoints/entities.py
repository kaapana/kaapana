from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, select, tuple_
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataEntityORM
from app.db.session import AsyncSessionLocal, get_async_db
from app.models.domain import DataEntity, StorageCoordinate
from app.models.events import EventAction
from app.models.query import EnsureEntityRequest, EnsureEntityResponse
from app.services.entity_query import QueryTranslationError, find_one_matching
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

# Retry budget for the SERIALIZABLE get-or-create loop. Under SSI two concurrent
# first-time creators of the same identity collide on commit; the loser aborts
# with a serialization failure, retries, and finds the winner. Converges in 1–2
# attempts in practice — the budget is a backstop against pathological churn.
_ENSURE_MAX_ATTEMPTS = 5

# Postgres SQLSTATEs that mean "the transaction was aborted, retry it":
# 40001 serialization_failure (SSI), 40P01 deadlock_detected.
_SERIALIZATION_SQLSTATES = {"40001", "40P01"}

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


def _is_serialization_failure(exc: DBAPIError) -> bool:
    """True if ``exc`` is a Postgres serialization/deadlock abort worth retrying."""
    sqlstate = getattr(getattr(exc, "orig", None), "sqlstate", None) or getattr(
        getattr(exc, "orig", None), "pgcode", None
    )
    return sqlstate in _SERIALIZATION_SQLSTATES


@router.post(
    "/ensure",
    response_model=EnsureEntityResponse,
    summary="Atomically get-or-create an entity matching a query",
)
async def ensure_entity(request: EnsureEntityRequest) -> EnsureEntityResponse:
    """Return the entity matching ``where``, or create ``entity`` if none matches.

    Atomic among concurrent callers: the find-then-create runs in a SERIALIZABLE
    transaction, so Postgres SSI predicate-locks the "no match" read and aborts
    one of two racing first-time creators with a serialization failure; the loser
    retries and its fresh snapshot now sees the winner, returning it with
    ``created=False``. Generic — the ``where`` query alone defines identity, so
    no unique column is needed on ``data_entities`` (unlike entity_links).

    The caller must pass an ``entity`` that itself satisfies ``where``; otherwise
    every call finds "no match" and creates another row → unbounded duplicates.

    NOTE: this serializes concurrent ``/entities/ensure`` callers only. A plain
    ``POST /entities`` that races in and creates a matching row is not covered.
    """
    last_exc: DBAPIError | None = None
    for _ in range(_ENSURE_MAX_ATTEMPTS):
        async with AsyncSessionLocal() as db:
            # Per-transaction isolation; the rest of the app stays READ COMMITTED.
            await db.connection(execution_options={"isolation_level": "SERIALIZABLE"})
            try:
                match = await find_one_matching(db, request.where)
            except (QueryTranslationError, ValueError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

            if match is not None:
                return EnsureEntityResponse(created=False, entity=match)

            db.add(entity_to_orm(request.entity))
            try:
                await db.commit()
            except DBAPIError as exc:
                await db.rollback()
                if _is_serialization_failure(exc):
                    last_exc = exc
                    continue  # retry: the winning row is now visible
                if isinstance(exc, IntegrityError):
                    # Almost always the caller reusing an existing entity id; the
                    # query-based contract expects a fresh id per attempt.
                    raise HTTPException(
                        status_code=409,
                        detail="Entity id already exists; supply a fresh id for ensure",
                    ) from exc
                raise

            created = await require_entity_response(db, request.entity.id)
        await broadcast_entity_event(EventAction.CREATED, created)
        return EnsureEntityResponse(created=True, entity=created)

    # Retries exhausted under sustained contention: one last read for the winner.
    async with AsyncSessionLocal() as db:
        match = await find_one_matching(db, request.where)
    if match is not None:
        return EnsureEntityResponse(created=False, entity=match)
    raise HTTPException(
        status_code=503,
        detail="Could not ensure entity under contention; retry",
    ) from last_exc


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
