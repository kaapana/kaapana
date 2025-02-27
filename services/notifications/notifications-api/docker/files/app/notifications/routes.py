import uuid
from datetime import datetime

import requests
from app.notifications.schemas import (
    Notification,
    NotificationDispatch,
    NotificationDispatchResponse,
)
from app.utils import AiiHelper, get_aii_helper
from app.websockets import ConnectionManager, get_connection_manager
from fastapi import APIRouter, Depends, HTTPException
from fastapi_versioning import version

router = APIRouter()


def notification_to_dispatch(
    notifcation: Notification, user_id: str = "", project_name: str = ""
) -> NotificationDispatch:
    return NotificationDispatch(
        id=uuid.uuid4(),
        user_id=user_id,
        project=project_name,
        timestamp=datetime.now(),
        **notifcation.dict(),  # Unpack the remaining fields from Notification
    )


def dispatch_to_response(
    dispatch: NotificationDispatch, n_total: int, n_dispatched: int = 0
) -> NotificationDispatchResponse:
    return NotificationDispatchResponse(
        notification_id=dispatch.id,
        success=n_dispatched
        > 0,  # success set to true if number of dispatched is more than 0
        active_connections=n_total,
        total_dispatched=n_dispatched,
        timestamp=dispatch.timestamp,
    )


@router.post(
    "/project/{project_name}",
    response_model=NotificationDispatchResponse,
    tags=["Dispatch"],
)
@version(1)
async def send_notification_to_project(
    project_name: str,
    notification_item: Notification,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
    aii_helper: AiiHelper = Depends(get_aii_helper),
):
    dispatch = notification_to_dispatch(notification_item, project_name=project_name)
    try:
        users = await aii_helper.fetch_project_users(project_name)
    except requests.exceptions.HTTPError as errh:
        raise HTTPException(
            status_code=500, detail=f"Failed to Fetch users. {errh.args[0]}"
        )

    n_dispatched, n_total = await con_mgr.send_notifications_to_users(dispatch, users)

    response = dispatch_to_response(dispatch, n_total, n_dispatched)
    return response


@router.post(
    "/project/{project_name}/user/{user_id}",
    response_model=NotificationDispatchResponse,
    tags=["Dispatch"],
)
@version(1)
async def send_notification_to_user_in_project(
    project_name: str,
    user_id: str,
    notification_item: Notification,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
    aii_helper: AiiHelper = Depends(get_aii_helper),
):
    dispatch = notification_to_dispatch(notification_item, project_name=project_name)
    try:
        users = await aii_helper.fetch_project_users(project_name)
    except requests.exceptions.HTTPError as errh:
        raise HTTPException(
            status_code=500, detail=f"Failed to Fetch users. {errh.args[0]}"
        )

    if user_id in users:
        n_dispatched, n_total = await con_mgr.send_notifications_to_users(
            dispatch, users
        )
        response = dispatch_to_response(dispatch, n_total, n_dispatched)
        return response
    else:
        raise HTTPException(
            status_code=404,
            detail=f"No user found with the provided user id in the project {project_name}",
        )


@router.post(
    "/user/{user_id}",
    response_model=NotificationDispatchResponse,
    tags=["Dispatch"],
)
@version(1)
async def send_notification_to_user(
    user_id: str,
    notification_item: Notification,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    dispatch = notification_to_dispatch(notification_item, user_id=user_id)

    users = [user_id]
    n_dispatched, n_total = await con_mgr.send_notifications_to_users(dispatch, users)

    response = dispatch_to_response(dispatch, n_total, n_dispatched)
    return response


@router.post(
    "/broadcast",
    response_model=NotificationDispatchResponse,
    tags=["Dispatch"],
)
@version(1)
async def send_notification_to_all(
    notification_item: Notification,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    dispatch = notification_to_dispatch(notification_item)

    n_dispatched, n_total = await con_mgr.broadcast_notifications(dispatch)

    response = dispatch_to_response(dispatch, n_total, n_dispatched)
    return response
