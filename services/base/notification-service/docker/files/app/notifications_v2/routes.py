from fastapi import APIRouter, Depends, HTTPException, Header, Query
from app.notifications_v2.schemas import (
    NotificationResponse,
    Metadata,
)
from app.notifications.models import Notification as NotificationModel
from app.dependencies import get_async_db
from sqlalchemy import select, delete, update, func, cast
from typing import Annotated
from datetime import datetime

router = APIRouter()


@router.get(
    "/",
    response_model=NotificationResponse,
    tags=["Frontend API"],
)
async def get_notifications(
    db=Depends(get_async_db),
    x_forwarded_user: Annotated[str | None, Header()] = None,
    cursor: datetime | None = Query(
        None, description="Fetch notifications older than this timestamp"
    ),
    limit: int = Query(
        20, ge=1, le=100, description="Maximum number of notifications to return"
    ),
):
    if not x_forwarded_user:
        raise HTTPException(400, "Missing user info")

    base_stmt = (
        select(NotificationModel)
        .where(NotificationModel.receivers.any(x_forwarded_user))
        .where(~NotificationModel.receviers_read.has_key(x_forwarded_user))
    )

    if cursor:
        base_stmt = base_stmt.where(NotificationModel.timestamp < cursor)

    stmt = base_stmt.order_by(NotificationModel.timestamp.desc()).limit(limit + 1)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    has_more = len(notifications) > limit
    notifications = notifications[:limit]

    next_cursor = notifications[-1].timestamp if has_more and notifications else None

    count_stmt = (
        select(func.count())
        .select_from(NotificationModel)
        .where(NotificationModel.receivers.any(x_forwarded_user))
        .where(~NotificationModel.receviers_read.has_key(x_forwarded_user))
    )

    total_result = await db.execute(count_stmt)
    total = total_result.scalar_one()

    return NotificationResponse(
        data=notifications,
        meta=Metadata(
            total=total,
            nextCursor=next_cursor,
            hasMore=has_more,
        ),
    )
