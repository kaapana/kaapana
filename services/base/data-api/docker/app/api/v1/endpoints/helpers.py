from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import DataEntityORM, MetadataSchemaORM
from app.models.domain import DataEntity, EntityLink
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


async def broadcast_link_event(action: EventAction, link: EntityLink) -> None:
    _broadcast_event(
        EventResource.LINK,
        action,
        id=str(link.id),
        source_id=str(link.source_id),
        target_id=str(link.target_id),
        link_type=link.link_type,
    )


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


async def validate_no_cycle(
    db: AsyncSession, source_id: UUID, target_id: UUID, link_type: str
) -> None:
    """Reject links that would close a cycle for the given link type.

    Walks forward from `target_id` along outgoing edges of the same link type;
    if `source_id` appears in that set, adding (source -> target) would create
    a cycle.
    """

    _MAX_CYCLE_WALK_DEPTH = 64

    if source_id == target_id:
        raise HTTPException(status_code=400, detail="Entity cannot link to itself")
    cte = text("""
        WITH RECURSIVE descendants(id, depth) AS (
            SELECT target_id, 1
              FROM entity_links
                            WHERE source_id = :target AND link_type = :link_type
            UNION
            SELECT el.target_id, d.depth + 1
              FROM entity_links el
              JOIN descendants d ON el.source_id = d.id
                            WHERE el.link_type = :link_type AND d.depth < :max_depth
        )
        SELECT 1 FROM descendants WHERE id = :source LIMIT 1
        """)
    result = await db.execute(
        cte,
        {
            "target": target_id,
            "source": source_id,
            "link_type": link_type,
            "max_depth": _MAX_CYCLE_WALK_DEPTH,
        },
    )
    if result.first() is not None:
        raise HTTPException(status_code=400, detail="Link would create a cycle")
