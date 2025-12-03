from fastapi import Request
import httpx

from app.alerts.service import AdminProjectResolver, NotificationForwarder


def get_http_client(request: Request) -> httpx.AsyncClient:
    client = getattr(request.app.state, "http_client", None)
    if client is None:
        raise RuntimeError("HTTP client not initialised")
    return client


def get_admin_project_resolver(request: Request) -> AdminProjectResolver:
    resolver = getattr(request.app.state, "admin_resolver", None)
    if resolver is None:
        raise RuntimeError("Admin project resolver not initialised")
    return resolver


def get_notification_forwarder(request: Request) -> NotificationForwarder:
    forwarder = getattr(request.app.state, "notification_forwarder", None)
    if forwarder is None:
        raise RuntimeError("Notification forwarder not initialised")
    return forwarder
