from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataEntityORM, MetadataSchemaORM
from app.models.domain import DataEntity
from app.models.events import EventAction, EventMessage, EventResource
from app.services.artifact_store import get_artifact_store
from app.services.entity_repository import entity_from_orm, fetch_entity_orm
from app.services.event_bus import get_event_bus

logger = logging.getLogger(__name__)


async def require_entity(db: AsyncSession, entity_id: UUID) -> DataEntityORM:
    entity = await fetch_entity_orm(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity


async def require_entity_response(db: AsyncSession, entity_id: UUID) -> DataEntity:
    entity = await fetch_entity_orm(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return entity_from_orm(entity)


async def commit_and_return_entity(db: AsyncSession, entity_id: UUID) -> DataEntity:
    await db.commit()
    return await require_entity_response(db, entity_id)


async def get_metadata_schema_optional(
    db: AsyncSession, key: str
) -> MetadataSchemaORM | None:
    stmt = select(MetadataSchemaORM).where(MetadataSchemaORM.key == key)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_metadata_schema(db: AsyncSession, key: str) -> MetadataSchemaORM:
    schema = await get_metadata_schema_optional(db, key)
    if schema is None:
        raise HTTPException(
            status_code=400, detail="Metadata schema not registered for key"
        )
    return schema


def _broadcast_event(resource: EventResource, action: EventAction, **data: Any) -> None:
    bus = get_event_bus()
    event = EventMessage.build(resource=resource, action=action, **data)

    async def _send() -> None:
        try:
            await bus.broadcast(event)
        except Exception:  # pragma: no cover - defensive log
            logger.exception("Failed to broadcast event")

    asyncio.create_task(_send())


async def broadcast_entity_event(
    action: EventAction, entity: DataEntity | UUID
) -> None:
    entity_id = entity.id if isinstance(entity, DataEntity) else entity
    _broadcast_event(EventResource.DATA_ENTITY, action, id=str(entity_id))


async def broadcast_metadata_key_event(
    action: EventAction, key: str, schema: dict | None = None
) -> None:
    payload: dict[str, Any] = {"key": key}
    if schema is not None:
        payload["schema"] = schema
    _broadcast_event(EventResource.METADATA_KEY, action, **payload)


def cleanup_entity_artifacts(entity_id: UUID | str) -> None:
    store = get_artifact_store()
    try:
        store.delete_entity(str(entity_id))
    except Exception:  # pragma: no cover - filesystem best effort
        logger.warning(
            "Failed to delete artifacts for entity %s", entity_id, exc_info=True
        )


def cleanup_metadata_artifacts(entity_id: UUID | str, key: str) -> None:
    store = get_artifact_store()
    try:
        store.delete_metadata_key(str(entity_id), key)
    except Exception:  # pragma: no cover - filesystem best effort
        logger.warning(
            "Failed to delete artifacts for entity %s metadata key %s",
            entity_id,
            key,
            exc_info=True,
        )


async def set_entity_parent(
    db: AsyncSession, entity: DataEntityORM, parent_id: UUID | None
) -> None:
    if parent_id is None:
        entity.parent = None
        return

    if parent_id == entity.id:
        raise HTTPException(status_code=400, detail="Entity cannot be its own parent")

    parent = await fetch_entity_orm(db, parent_id)
    if parent is None:
        raise HTTPException(status_code=400, detail="Parent entity not found")

    ancestor = parent
    while ancestor is not None:
        if ancestor.id == entity.id:
            raise HTTPException(
                status_code=400, detail="Parent link would create a cycle"
            )
        ancestor = ancestor.parent

    entity.parent = parent
