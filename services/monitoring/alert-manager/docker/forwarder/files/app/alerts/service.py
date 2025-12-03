import logging
import time
from datetime import datetime
from typing import Any

import httpx
from fastapi import HTTPException

from app.alerts.schemas import Alert, AlertmanagerWebhook, NotificationPayload
from app.config import settings

logger = logging.getLogger(__name__)


class AdminProjectResolver:
    def __init__(
        self, client: httpx.AsyncClient, base_url: str, cache_ttl: int
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._cache_ttl = cache_ttl
        self._cached_id: str | None = None
        self._cached_ts = 0.0

    async def get_project_id(self) -> str:
        now = time.monotonic()
        if self._cached_id and now - self._cached_ts < self._cache_ttl:
            return self._cached_id
        await self._refresh()
        if not self._cached_id:
            raise RuntimeError("Admin project id missing after refresh")
        return self._cached_id

    async def _refresh(self) -> None:
        url = f"{self._base_url}/projects/admin"
        try:
            response = await self._client.get(url)
        except httpx.RequestError as exc:
            logger.exception("Failed to reach Access Information Interface: %s", exc)
            raise HTTPException(
                status_code=502, detail="Failed to reach Access Information Interface"
            ) from exc

        if response.status_code == 404:
            raise HTTPException(status_code=502, detail="Admin project not yet found")

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception("AII responded with %s", exc.response.text)
            raise HTTPException(
                status_code=502, detail="Access Information Interface error"
            ) from exc

        data = response.json()
        project_id = data.get("id")
        if not project_id:
            logger.error("Admin project response missing id field: %s", data)
            raise HTTPException(
                status_code=502, detail="Malformed admin project response"
            )
        self._cached_id = project_id
        self._cached_ts = time.monotonic()


class NotificationForwarder:
    def __init__(self, client: httpx.AsyncClient, base_url: str) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")

    async def send(self, project_id: str, payload: NotificationPayload) -> None:
        url = f"{self._base_url}/{project_id}"
        try:
            response = await self._client.post(url, json=payload.model_dump())
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.exception(
                "Notification service rejection (%s): %s",
                exc.response.status_code,
                exc.response.text,
            )
            raise HTTPException(
                status_code=exc.response.status_code,
                detail="Notification service rejected alert",
            ) from exc
        except httpx.RequestError as exc:
            logger.exception("Failed to reach notification service: %s", exc)
            raise HTTPException(
                status_code=502, detail="Notification service unreachable"
            ) from exc


def _severity_from_labels(labels: dict[str, Any]) -> str:
    return str(labels.get("severity", "info")).lower()


def _pick_first_link(payload: AlertmanagerWebhook) -> str | None:
    for alert in payload.alerts:
        if alert.generatorURL:
            return alert.generatorURL
    return payload.externalURL


def _format_dt(value: datetime | None) -> str:
    if not value:
        return "n/a"
    return value.isoformat()


def _render_alert_section(alert: Alert) -> str:
    summary = (
        alert.annotations.get("summary")
        or alert.annotations.get("description")
        or "No summary provided."
    )
    label_items = "".join(
        f"<li><b>{key}:</b> {value}</li>" for key, value in sorted(alert.labels.items())
    )
    meta_items = [
        f"<li><b>Status:</b> {alert.status}</li>"
        f"<li><b>Starts:</b> {_format_dt(alert.startsAt)}</li>"
        f"<li><b>Ends:</b> {_format_dt(alert.endsAt)}</li>"
    ]
    if alert.generatorURL:
        meta_items.append(
            f'<li><b>Source:</b> <a href="{alert.generatorURL}">{alert.generatorURL}</a></li>'
        )
    return (
        "<section>"
        f"<h4>{alert.labels.get('alertname', 'Alert')}</h4>"
        f"<p>{summary}</p>"
        f"<ul>{label_items}{''.join(meta_items)}</ul>"
        "</section>"
    )


def _build_description(payload: AlertmanagerWebhook) -> str:
    sections = [_render_alert_section(alert) for alert in payload.alerts]
    return "".join(sections)


def _choose_icon(severity: str) -> str:
    match severity:
        case "critical":
            return "mdi-alert-octagram"
        case "warning" | "warn":
            return "mdi-alert"
        case "info" | "information":
            return "mdi-information"
        case _:
            return settings.default_icon


def build_notification(payload: AlertmanagerWebhook) -> NotificationPayload:
    if not payload.alerts:
        raise HTTPException(status_code=400, detail="Payload did not contain alerts")

    base_labels = payload.commonLabels or payload.alerts[0].labels
    severity = _severity_from_labels(base_labels)
    summary = (
        (payload.commonAnnotations or {}).get("summary")
        or payload.alerts[0].annotations.get("summary")
        or payload.alerts[0].labels.get("alertname")
        or "Alertmanager notification"
    )

    description = _build_description(payload)
    topic = f"{settings.topic_prefix} - {severity.upper()}"
    link = _pick_first_link(payload)
    icon = _choose_icon(severity)

    return NotificationPayload(
        topic=topic,
        title=summary,
        description=description,
        icon=icon,
        link=link,
    )
