from fastapi import APIRouter, HTTPException, Request, Response
from helpers.provider_availability import registered_providers
from models.provider import ProviderRegistration
from helpers.wazuh import WazuhAPIAuthentication, WazuhAPIWrapper
import logging
from helpers.resources import API_ROUTE_PREFIX, LOGGER_NAME
from helpers.logger import get_logger
from starlette.status import HTTP_200_OK, HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR

logger = get_logger(f"{LOGGER_NAME}.api", logging.INFO)

router = APIRouter(prefix=f"/{API_ROUTE_PREFIX}")
wazuh_authentication = WazuhAPIAuthentication()

# export interface SecurityProvider {
#   id: string;
#   name: string;
#   url: string;
#   api_endpoints: string[];
# }

@router.get("/provider")
def get_provider():
    return {"provider": registered_providers.get_overview()}

@router.put("/provider")
def put_provider(provider: ProviderRegistration):
    registered_providers.add(provider)  

# todo change route
@router.get("/extension/wazuh/agent-installed")
def get_wazuh_agent_installed():
    try:
        wazuh_api = WazuhAPIWrapper(wazuh_authentication)
        return {"agent_installed": wazuh_api.is_agent_installed()}
    except:
        raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve information about installed Wazuh agents")

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

# get data dump from specific extension
#@router.get("/extension/{extension-name}")

# todo: make wazuh and stackrox specific apis and enable them once registration is made
# todo: find a way to encapsulate event_registrations and provider specific data

@router.get("/{full_path:path}")
def catch_all_api(request: Request, full_path:str):
    raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="API route not available")

