from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Alert(BaseModel):
    status: str
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    startsAt: datetime | None = None
    endsAt: datetime | None = None
    generatorURL: str | None = None
    fingerprint: str | None = None


class AlertmanagerWebhook(BaseModel):
    receiver: str | None = None
    status: str
    alerts: list[Alert] = Field(default_factory=list)
    groupLabels: dict[str, Any] = Field(default_factory=dict)
    commonLabels: dict[str, Any] = Field(default_factory=dict)
    commonAnnotations: dict[str, Any] = Field(default_factory=dict)
    externalURL: str | None = None
    version: str | None = None
    truncatedAlerts: int | None = None


class NotificationPayload(BaseModel):
    topic: str | None
    title: str
    description: str
    icon: str | None = None
    link: str | None = None
