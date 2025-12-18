import logging
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.alerts.schemas import AlertmanagerWebhook
from app.alerts.service import (
    AdminProjectResolver,
    NotificationForwarder,
    build_notification,
)
from app.dependencies import get_admin_project_resolver, get_notification_forwarder

router = APIRouter(tags=["Alerts"])

load_logger = logging.getLogger(__name__)


@router.get("/health", response_class=JSONResponse)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/alerts", status_code=status.HTTP_202_ACCEPTED)
async def forward_alert(
    payload: AlertmanagerWebhook,
    resolver: AdminProjectResolver = Depends(get_admin_project_resolver),
    forwarder: NotificationForwarder = Depends(get_notification_forwarder),
) -> dict[str, object]:
    notification = build_notification(payload)
    project_id = await resolver.get_project_id()
    await forwarder.send(project_id, notification)
    message = {
        "status": "forwarded",
        "project_id": project_id,
        "alerts": len(payload.alerts),
    }
    load_logger.info(message)
    return message
