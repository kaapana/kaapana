import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, HTTPException
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory
from api_access.wazuh_api import WazuhAPIAuthentication, WazuhAPIWrapper
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from routers.deactivatable_router import DeactivatableRouter
from models.provider import ProviderAPIEndpoints
from models.misc import SecurityNotification

logger = get_logger(f"{LOGGER_NAME}.wazuh_router", logging.INFO)


class WazuhRouter(DeactivatableRouter):
    router = APIRouter(prefix=f"/wazuh", redirect_slashes=True)
    __wazuh_authentication = WazuhAPIAuthentication()
    __ui_url: Optional[str] = None
    __wazuh_api: Optional[WazuhAPIWrapper] = None
    __current_notifications: List[SecurityNotification] = []
    __notification_task = None
    __notification_task_activated = False

    def __init__(self, activated=False):
        self.router.add_api_route("/url", self.get_wazuh_url, methods=["GET"])
        self.router.add_api_route(
            "/agent-installed", self.get_wazuh_agent_installed, methods=["GET"]
        )
        self.router.add_api_route("/agents", self.get_wazuh_agents, methods=["GET"])
        self.router.add_api_route(
            "/agents/{agent_id}/sca", self.get_agent_sca_policies, methods=["GET"]
        )  # security compatibility assessment policy
        self.router.add_api_route(
            "/agents/{agent_id}/sca/{policy_id}",
            self.get_agent_sca_policy_checks,
            methods=["GET"],
        )  # security compatibility assessment
        self.router.add_api_route(
            "/agents/{agent_id}/vulnerabilities",
            self.get_agent_vulnerabilities,
            methods=["GET"],
        )
        self.router.add_api_route(
            "/agents/{agent_id}/file-integrity-alerts",
            self.get_agent_file_integrity_alerts,
            methods=["GET"],
        )

        self.__notification_task = asyncio.create_task(self.__get_new_events())
        self._activated = activated

    async def __get_new_events(self) -> None:
        fetch_interval = 10
        keep_for_seconds = fetch_interval * 2

        while True:
            if self.__notification_task_activated:
                logger.debug(
                    f"fetching notifications, old: {self.__current_notifications}"
                )

                # remove old notifications
                new_notifications: List[SecurityNotification] = []
                for notification in self.__current_notifications:
                    # check if notification timestamp is older than `keep_for_seconds` seconds
                    if (
                        datetime.now(timezone.utc) - notification.timestamp
                    ).total_seconds() <= keep_for_seconds:
                        new_notifications += [notification]

                # fetch new events from wazuh
                if self.__wazuh_api is not None:
                    new_notifications += self.__wazuh_api.get_new_events(
                        self.__ui_url, fetch_interval + 5
                    )

                self.__current_notifications = new_notifications
                logger.debug(f"new notifications: {self.__current_notifications}")

            await asyncio.sleep(fetch_interval)

    @function_logger_factory(logger)
    def set_activated(self, activated: bool):
        logger.debug(f"set route active: {activated}")
        self._activated = activated

    @function_logger_factory(logger)
    def set_endpoints(self, ui_url: str, api_endpoints: List[ProviderAPIEndpoints]):
        logger.debug(f"setting endpoints, ui url: {ui_url}, others: {api_endpoints}")
        self.__ui_url = ui_url
        self.__wazuh_api = WazuhAPIWrapper(self.__wazuh_authentication, api_endpoints)
        self.__notification_task_activated = True

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_wazuh_url(self):
        if self.__ui_url is not None and self.__ui_url != "":
            return {"url": self.__ui_url}
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Url not available"
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_wazuh_agent_installed(self):
        try:
            return {"agent_installed": self.__wazuh_api.is_agent_installed()}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve whether or not a Wazuh agent is installed",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_wazuh_agents(self):
        try:
            return {"agents": self.__wazuh_api.get_all_agents()}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve information about Wazuh agents",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_agent_sca_policies(self, agent_id: str):
        try:
            return {"sca_policies": self.__wazuh_api.get_agent_sca_policies(agent_id)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve information about Wazuh agent {agent_id} security compatibility assessment policies",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_agent_sca_policy_checks(self, agent_id: str, policy_id: str):
        try:
            return {
                "sca_policy_checks": self.__wazuh_api.get_agent_sca_policy_checks(
                    agent_id, policy_id
                )
            }  # todo pagination?
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve information about Wazuh agent {agent_id} security compatibility assessment",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_agent_file_integrity_alerts(self, agent_id: str):
        try:
            return {
                "file_integrity_alerts": self.__wazuh_api.get_agent_file_integrity_alerts(
                    agent_id
                )
            }  # todo pagination?
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve information about Wazuh agent {agent_id} file integrity alerts",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    async def get_agent_vulnerabilities(self, agent_id: str):
        try:
            return {
                "vulnerabilities": await self.__wazuh_api.get_agent_vulnerabilities(
                    agent_id
                )
            }  # todo pagination?
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Could not retrieve information about Wazuh agent {agent_id} vulnerabilities",
            )

    @function_logger_factory(logger)
    def get_notifcations(self) -> List[SecurityNotification]:
        return self.__current_notifications
