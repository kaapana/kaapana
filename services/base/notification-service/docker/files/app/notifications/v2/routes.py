from datetime import datetime, timezone
from typing import Annotated
from uuid import UUID

from app.dependencies import get_access_service, get_async_db, get_connection_manager
from app.models import Notification as NotificationModel
from app.notifications.v2.schemas import (
    Metadata,
    Notification,
    NotificationCreate,
    NotificationCreateNoReceivers,
    NotificationResponse,
)
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import cast, delete, func, select, update
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, TEXT

router = APIRouter()


async def add_notification(
    notification: NotificationModel, db, con_mgr
) -> NotificationModel:
    db.add(notification)
    await db.commit()
    await db.refresh(notification)
    await con_mgr.notify_new_notification(
        user_ids=notification.receivers, id=notification.id
    )
    return notification


async def get_users(project_id: str, access_service):
    try:
        users = await access_service.fetch_user_ids(project_id)
    except Exception as e:
        raise HTTPException(502, "Upsream AII request failed")
    if users is None:
        raise HTTPException(404, f"Project {project_id} not found")
    if not users:
        raise HTTPException(422, f"Project {project_id} has no non-system users")
    return users


@router.post("/{project_id}", response_model=Notification, tags=["Service"])
async def post_notification_project(
    project_id: str,
    n: NotificationCreateNoReceivers,
    db=Depends(get_async_db),
    access_service=Depends(get_access_service),
    con_mgr=Depends(get_connection_manager),
):
    users = await get_users(project_id, access_service)
    notification = NotificationModel(
        topic=n.topic,
        title=n.title,
        description=n.description,
        icon=n.icon,
        link=n.link,
        receivers=users,
    )
    return await add_notification(notification, db, con_mgr)


@router.post("/{project_id}/{user_id}", response_model=Notification, tags=["Service"])
async def post_notification_user(
    project_id: str,
    user_id: str,
    n: NotificationCreateNoReceivers,
    db=Depends(get_async_db),
    access_service=Depends(get_access_service),
    con_mgr=Depends(get_connection_manager),
):
    users = await get_users(project_id, access_service)

    if user_id not in users:
        raise HTTPException(
            404, f"User ID {user_id} not present in project {project_id}"
        )
    notification = NotificationModel(
        topic=n.topic,
        title=n.title,
        description=n.description,
        icon=n.icon,
        link=n.link,
        receivers=[user_id],
    )
    return await add_notification(notification, db, con_mgr)


@router.post("/", response_model=Notification, tags=["Service"])
async def post_notification(
    n: NotificationCreate,
    db=Depends(get_async_db),
    access_service=Depends(get_access_service),
    con_mgr=Depends(get_connection_manager),
):
    for user_id in n.receivers:
        if not await access_service.user_exists(user_id):
            raise HTTPException(404, f"User ID {user_id} not valid")

    notification = NotificationModel(
        topic=n.topic,
        title=n.title,
        description=n.description,
        icon=n.icon,
        link=n.link,
        receivers=n.receivers,
    )
    return await add_notification(notification, db, con_mgr)


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


@router.put("/read", tags=["Frontend API"])
async def mark_all_read(
    x_forwarded_user: Annotated[str | None, Header()] = None,
    db=Depends(get_async_db),
    con_mgr=Depends(get_connection_manager),
) -> list[UUID]:
    """Mark every unread notification of the caller as read.

    One statement and one websocket event however long the (paginated) list
    is; the per-id endpoint would cost one request and one event each.
    """
    if not x_forwarded_user:
        raise HTTPException(400, "Missing user info")
    user = x_forwarded_user

    now = datetime.now(timezone.utc)
    stmt = (
        update(NotificationModel)
        .where(NotificationModel.receivers.any(user))
        .where(~NotificationModel.receviers_read.has_key(user))
        .values(
            receviers_read=func.jsonb_set(
                NotificationModel.receviers_read,
                cast([user], ARRAY(TEXT)),
                cast(func.to_jsonb(now), JSONB),
                True,
            )
        )
        .returning(NotificationModel.id)
    )
    ids = list((await db.execute(stmt)).scalars().all())
    if ids:
        # Same rule as the per-id endpoint: once every recipient has read a
        # notification it is dropped.
        await db.execute(
            delete(NotificationModel)
            .where(NotificationModel.id.in_(ids))
            .where(
                NotificationModel.receviers_read.has_all(NotificationModel.receivers)
            )
        )
    await db.commit()
    if ids:
        await con_mgr.notify_read_all(user_ids=[user])
    return ids


@router.put("/{notification_id}/read", tags=["Frontend API"])
async def mark_read(
    notification_id: UUID,
    x_forwarded_user: Annotated[str | None, Header()] = None,
    db=Depends(get_async_db),
    con_mgr=Depends(get_connection_manager),
):
    if not x_forwarded_user:
        raise HTTPException(400, "Missing user info")
    user = x_forwarded_user

    notification = (
        await db.execute(
            select(NotificationModel)
            .where(NotificationModel.id == notification_id)
            .where(NotificationModel.receivers.any(x_forwarded_user))
        )
    ).scalar_one_or_none()

    if not notification:
        raise HTTPException(404, f"Notification with id {notification_id} not found")

    now = datetime.now(timezone.utc)
    stmt = (
        update(NotificationModel)
        .where(NotificationModel.id == notification_id)
        .where(NotificationModel.receviers_read[user].is_(None))
        .values(
            receviers_read=func.jsonb_set(
                NotificationModel.receviers_read,
                cast([user], ARRAY(TEXT)),
                cast(func.to_jsonb(now), JSONB),
                True,
            )
        )
        .returning(NotificationModel.id)
    )
    await db.execute(stmt)
    await db.commit()
    await con_mgr.notify_read_notification(user_ids=[user], id=notification_id)

    # If notification is read by all recipients it is delete form the database
    notification = (
        await db.execute(
            select(NotificationModel).where(NotificationModel.id == notification_id)
        )
    ).scalar_one_or_none()
    if not notification:
        # Notification is already deleted
        return

    all_read = all(
        user in notification.receviers_read for user in notification.receivers
    )
    print(all_read)

    if all_read:
        await db.execute(
            delete(NotificationModel).where(NotificationModel.id == notification_id)
        )
        await db.commit()
