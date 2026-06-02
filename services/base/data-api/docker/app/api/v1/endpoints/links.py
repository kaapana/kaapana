from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EntityLinkORM
from app.db.session import get_async_db
from app.models.domain import EntityLink, EntityLinkCreate
from app.models.events import EventAction
from app.services.entity_repository import link_from_orm

from .helpers import broadcast_link_event, require_entity, validate_no_cycle

router = APIRouter(prefix="/entities", tags=["links"])


def _normalize_link_type(value: str) -> str:
    token = value.strip().lower()
    if not token:
        raise HTTPException(status_code=400, detail="link_type must not be empty")
    return token


@router.post(
    "/{source_id}/links",
    response_model=EntityLink,
    summary="Create a directed link from this entity to another",
)
async def create_link(
    source_id: UUID,
    body: EntityLinkCreate,
    db: AsyncSession = Depends(get_async_db),
) -> EntityLink:
    link_type = _normalize_link_type(body.link_type)

    await require_entity(db, source_id)
    await require_entity(db, body.target_id)

    if source_id == body.target_id:
        raise HTTPException(status_code=400, detail="Entity cannot link to itself")

    CONTAINS_LINK_TYPE = "contains"
    if link_type == CONTAINS_LINK_TYPE:
        await validate_no_cycle(db, source_id, body.target_id, link_type)

    orm = EntityLinkORM(
        source_id=source_id,
        target_id=body.target_id,
        link_type=link_type,
        properties=dict(body.properties or {}),
    )
    db.add(orm)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A link with this source, target, and type already exists",
        ) from exc

    await db.refresh(orm)
    link = link_from_orm(orm)
    await broadcast_link_event(EventAction.CREATED, link)
    return link


@router.delete(
    "/{source_id}/links/{link_id}",
    status_code=204,
    summary="Delete a directed link",
)
async def delete_link(
    source_id: UUID,
    link_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> Response:
    stmt = select(EntityLinkORM).where(
        EntityLinkORM.id == link_id, EntityLinkORM.source_id == source_id
    )
    result = await db.execute(stmt)
    orm = result.scalar_one_or_none()
    if orm is None:
        raise HTTPException(status_code=404, detail="Link not found")

    link = link_from_orm(orm)
    await db.delete(orm)
    await db.commit()
    await broadcast_link_event(EventAction.DELETED, link)
    return Response(status_code=204)
