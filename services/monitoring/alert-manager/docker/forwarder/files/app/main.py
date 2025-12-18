import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any
import httpx

from fastapi import FastAPI
from pydantic import Field

from app.alerts.routes import router as alerts_router
from app.alerts.service import AdminProjectResolver, NotificationForwarder
from app.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    timeout = httpx.Timeout(
        settings.http_timeout, connect=settings.http_connect_timeout
    )
    client = httpx.AsyncClient(timeout=timeout)
    app.state.http_client = client
    app.state.admin_resolver = AdminProjectResolver(
        client, settings.aii_base_url, settings.admin_project_cache_ttl
    )
    app.state.notification_forwarder = NotificationForwarder(
        client, settings.notification_service_url
    )
    yield
    await client.aclose()


app = FastAPI(
    title="Alertmanager Forwarder",
    version="0.1.0",
    summary="Translate Alertmanager webhook payloads into Kaapana notifications",
    lifespan=lifespan,
)

app.include_router(alerts_router)
commonAnnotations: dict[str, Any] = Field(default_factory=dict)
