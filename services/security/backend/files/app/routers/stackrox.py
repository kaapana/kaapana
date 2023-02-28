from functools import wraps
from fastapi import APIRouter, HTTPException, Request, Response
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory
from helpers.wazuh import WazuhAPIAuthentication, WazuhAPIWrapper
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from routers.deactivatable_router import DeactivatableRouter

logger = get_logger(f"{LOGGER_NAME}.stackrox_router", logging.INFO)


class StackRoxRouter(DeactivatableRouter):
    router = APIRouter(prefix=f"/stackrox", redirect_slashes=True)
    # __wazuh_authentication = WazuhAPIAuthentication()

    def __init__(self, activated=False):
        # self.router.add_api_route("/agent-installed", self.get_wazuh_agent_installed, methods=["GET"])
        self._activated = activated

    @function_logger_factory(logger)
    def set_activated(self, activated: bool):
        logger.debug(f"Set route active: {activated}")
        self._activated = activated

    # @DeactivatableRouter.activation_wrapper
    # @function_logger_factory(logger)
    # def get_wazuh_agent_installed(self):
    #     try:
    #         wazuh_api = WazuhAPIWrapper(self.__wazuh_authentication)
    #         return {"agent_installed": wazuh_api.is_agent_installed()}
    #     except:
    #         raise HTTPException(status_code=HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not retrieve information about installed Wazuh agents")
