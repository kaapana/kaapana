from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, List, Tuple
from uuid import UUID

from sqlalchemy import Select, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import load_only, selectinload

from app.db.models import (
    ArtifactORM,
    DataEntityORM,
    MetadataEntryORM,
    StorageCoordinateORM,
)
from app.models.domain import (
    Artifact,
    BaseStorageCoordinate,
    DataEntity,
    FilesystemStorageCoordinate,
    MetadataEntry,
    PacsStorageCoordinate,
    S3StorageCoordinate,
    StorageCoordinate,
    StoreType,
    UrlStorageCoordinate,
)


_STORAGE_TYPE_MAP: dict[StoreType, type[BaseStorageCoordinate]] = {
    StoreType.PACS: PacsStorageCoordinate,
    StoreType.S3: S3StorageCoordinate,
    StoreType.FILESYSTEM: FilesystemStorageCoordinate,
    StoreType.URL: UrlStorageCoordinate,
}


def _entity_select() -> Select[tuple[DataEntityORM]]:
    return select(DataEntityORM).options(
        selectinload(DataEntityORM.storage_coordinates),
        selectinload(DataEntityORM.metadata_entries).selectinload(
            MetadataEntryORM.artifacts
        ),
        selectinload(DataEntityORM.parent).load_only(DataEntityORM.id),
        selectinload(DataEntityORM.children).load_only(DataEntityORM.id),
    )


async def fetch_entity_orm(
    session: AsyncSession, entity_id: UUID
) -> DataEntityORM | None:
    stmt = _entity_select().where(DataEntityORM.id == entity_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def fetch_all_entity_orms(session: AsyncSession) -> List[DataEntityORM]:
    result = await session.execute(_entity_select())
    return result.scalars().unique().all()


def _creation_order() -> tuple[Any, Any]:
    return (DataEntityORM.created_at, DataEntityORM.id)


async def _cursor_tuple(
    session: AsyncSession, entity_id: UUID
) -> Tuple[datetime, UUID]:
    stmt = select(DataEntityORM.created_at, DataEntityORM.id).where(
        DataEntityORM.id == entity_id
    )
    result = await session.execute(stmt)
    row = result.one_or_none()
    if row is None:
        raise ValueError("Cursor ID not found")
    created_at, entity_id = row
    return created_at, entity_id


async def resolve_entity_cursor(
    session: AsyncSession, entity_id: UUID
) -> Tuple[datetime, UUID]:
    return await _cursor_tuple(session, entity_id)


async def execute_entity_query(
    session: AsyncSession,
    request: QueryRequest,
) -> tuple[list[DataEntity], int, UUID | None]:
    predicate = _build_query_predicate(request.where)
    total_count = await _count_entities(session, predicate)

    limit = request.limit or 100
    stmt = _entity_select()
    if predicate is not None:
        stmt = stmt.where(predicate)

    stmt = stmt.order_by(*_creation_order()).limit(limit + 1)
    if request.cursor:
        created_at, cursor_id = await _cursor_tuple(session, request.cursor)
        stmt = stmt.where(
            tuple_(DataEntityORM.created_at, DataEntityORM.id)
            > tuple_(created_at, cursor_id)
        )

    result = await session.execute(stmt)
    rows = result.scalars().unique().all()
    has_more = len(rows) > limit
    page = rows[:limit]
    next_cursor = page[-1].id if has_more and page else None
    return entities_from_orms(page), total_count, next_cursor


async def _count_entities(
    session: AsyncSession, predicate: ColumnElement[bool] | None
) -> int:
    stmt = select(func.count(DataEntityORM.id))
    if predicate is not None:
        stmt = stmt.where(predicate)
    result = await session.execute(stmt)
    scalar = result.scalar_one()
    return int(scalar or 0)


async def fetch_entity_page(
    session: AsyncSession,
    *,
    cursor: UUID | None,
    limit: int,
) -> List[DataEntityORM]:
    stmt = _entity_select().order_by(*_creation_order()).limit(limit + 1)
    if cursor:
        created_at, entity_id = await _cursor_tuple(session, cursor)
        stmt = stmt.where(
            tuple_(DataEntityORM.created_at, DataEntityORM.id)
            > tuple_(created_at, entity_id)
        )
    result = await session.execute(stmt)
    return result.scalars().unique().all()


def _storage_cls_for(store_type: str) -> type[BaseStorageCoordinate]:
    store_enum = StoreType(store_type)
    return _STORAGE_TYPE_MAP[store_enum]


def storage_from_orm(orm: StorageCoordinateORM) -> StorageCoordinate:
    payload = dict(orm.details or {})
    payload.setdefault("type", orm.type)
    storage_cls = _storage_cls_for(payload["type"])
    return storage_cls.model_validate(payload)


def storage_to_orm(coord: StorageCoordinate) -> StorageCoordinateORM:
    payload = coord.model_dump(mode="json")
    return StorageCoordinateORM(type=coord.type.value, details=payload)


def artifact_from_orm(orm: ArtifactORM) -> Artifact:
    return Artifact(
        id=orm.artifact_id,
        filename=orm.filename,
        content_type=orm.content_type,
        size_bytes=orm.size_bytes,
    )


def artifact_to_orm(artifact: Artifact) -> ArtifactORM:
    return ArtifactORM(
        artifact_id=artifact.id,
        filename=artifact.filename,
        content_type=artifact.content_type,
        size_bytes=artifact.size_bytes,
    )


def metadata_entry_from_orm(orm: MetadataEntryORM) -> MetadataEntry:
    return MetadataEntry(
        key=orm.key,
        data=orm.data or {},
        artifacts=[artifact_from_orm(a) for a in orm.artifacts],
    )


def metadata_entry_to_orm(entry: MetadataEntry) -> MetadataEntryORM:
    return MetadataEntryORM(
        key=entry.key,
        data=entry.data or {},
        artifacts=[artifact_to_orm(a) for a in entry.artifacts],
    )


def entity_from_orm(orm: DataEntityORM) -> DataEntity:
    return DataEntity(
        id=orm.id,
        created_at=orm.created_at,
        parent_id=orm.parent.id if orm.parent else None,
        child_ids=sorted(
            (child.id for child in orm.children), key=lambda value: value.hex
        ),
        storage_coordinates=[
            storage_from_orm(coord) for coord in orm.storage_coordinates
        ],
        metadata=[metadata_entry_from_orm(m) for m in orm.metadata_entries],
    )


def entity_to_orm(entity: DataEntity) -> DataEntityORM:
    orm = DataEntityORM(
        id=entity.id,
        storage_coordinates=[
            storage_to_orm(coord) for coord in entity.storage_coordinates
        ],
        metadata_entries=[metadata_entry_to_orm(entry) for entry in entity.metadata],
    )
    if entity.created_at is not None:
        orm.created_at = entity.created_at
    return orm


def entities_from_orms(orms: Iterable[DataEntityORM]) -> List[DataEntity]:
    return [entity_from_orm(orm) for orm in orms]
