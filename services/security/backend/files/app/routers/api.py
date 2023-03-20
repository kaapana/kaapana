from typing import Callable, List
from fastapi import APIRouter, HTTPException, Request, Response
from helpers.provider_availability import RegisteredProviders
from models.provider import (
    ProviderRegistration,
    ProviderRegistrationOverview,
    ProviderType,
)
from routers.wazuh_router import WazuhRouter
from routers.stackrox_router import StackRoxRouter
import logging
from helpers.resources import API_ROUTE_PREFIX, LOGGER_NAME
from helpers.logger import get_logger
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND
from models.misc import Notification, SecurityNotification
from models.response import Response as ResponseModel

logger = get_logger(f"{LOGGER_NAME}.api", logging.INFO)

router = APIRouter(prefix=f"/{API_ROUTE_PREFIX}", redirect_slashes=True)
wazuh_router: WazuhRouter = WazuhRouter()
stackrox_router: StackRoxRouter = StackRoxRouter()


def on_provider_available(provider_type: ProviderType):
    logger.debug(f"provider available: {provider_type}")
    if provider_type == ProviderType.WAZUH and wazuh_router is not None:
        wazuh_router.set_activated(True)
    elif provider_type == ProviderType.STACKROX and stackrox_router is not None:
        stackrox_router.set_activated(True)


def on_provider_unavailable(provider_type: ProviderType):
    logger.debug(f"provider unavailable: {provider_type}")
    if provider_type == ProviderType.WAZUH and wazuh_router is not None:
        wazuh_router.set_activated(False)
    elif provider_type == ProviderType.STACKROX and stackrox_router is not None:
        stackrox_router.set_activated(False)


def on_provider_added(provider_type: ProviderType, provider: ProviderRegistration):
    if provider_type == ProviderType.WAZUH:
        wazuh_router.set_endpoints(provider.url, provider.api_endpoints)
    elif provider_type == ProviderType.STACKROX:
        stackrox_router.set_endpoints(provider.url, provider.api_endpoints)


registered_providers = RegisteredProviders(
    on_provider_added, on_provider_available, on_provider_unavailable
)


@router.get(
    "/providers", response_model=ResponseModel[List[ProviderRegistrationOverview]]
)
def get_provider():
    return {"data": registered_providers.get_overview()}


@router.put("/providers")
def put_provider(provider: ProviderRegistration):
    registered_providers.add(provider)
    return Response(status_code=HTTP_200_OK)


router.include_router(wazuh_router.router, prefix="/providers")
router.include_router(stackrox_router.router, prefix="/providers")


@router.get("/enable-debug")
def get_enable_debug():
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(logging.DEBUG)
    return Response(status_code=HTTP_200_OK)


@router.get("/disable-debug")
def get_disable_debug():
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).setLevel(logging.INFO)
    return Response(status_code=HTTP_200_OK)


# todo: get alerts from stackrox and also include errors from fastapi
@router.get("/notifications", response_model=ResponseModel[List[Notification]])
def get_notifications(response: Response):
    response.headers["max-age"] = "5"

    strip_notification_timestamp: Callable[
        [SecurityNotification], Notification
    ] = lambda notification: {
        "title": notification.title,
        "description": notification.description,
        "link": notification.link,
    }
    wazuh_notifications = list(
        map(strip_notification_timestamp, wazuh_router.get_notifcations())
    )
    stackrox_notifications = []
    # stackrox_notifications = list(map(strip_notification_timestamp, stackrox_router.get_notifcations()))
    return {"data": [*wazuh_notifications, *stackrox_notifications]}


@router.get("/{full_path:path}")
def catch_all_api(request: Request, full_path: str):
    raise HTTPException(
        status_code=HTTP_404_NOT_FOUND, detail="API route not available"
    )
