from functools import wraps
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Request, Response
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory
from api_access.stackrox_api import (
    StackRoxAPIAuthentication,
    StackRoxAPIWrapper,
)  # , StackRoxAPIWrapper
from starlette.status import HTTP_404_NOT_FOUND, HTTP_500_INTERNAL_SERVER_ERROR
from routers.deactivatable_router import DeactivatableRouter
from models.provider import ProviderAPIEndpoints
from models.response import Response as ResponseModel
from models.stackrox_models import Deployment, Image, PolicyViolation, Secret

logger = get_logger(f"{LOGGER_NAME}.stackrox_router", logging.INFO)


class StackRoxRouter(DeactivatableRouter):
    router = APIRouter(prefix=f"/stackrox", redirect_slashes=True)
    __stackrox_authentication = StackRoxAPIAuthentication()
    __ui_url: Optional[str] = None
    __stackrox_api: Optional[StackRoxAPIWrapper] = None

    def __init__(self, activated=False):
        self.router.add_api_route(
            "/url",
            self.get_stackrox_url,
            methods=["GET"],
            response_model=ResponseModel[str],
        )
        self.router.add_api_route(
            "/networkgraph-url",
            self.get_network_graph_url,
            methods=["GET"],
            response_model=ResponseModel[str],
        )
        self.router.add_api_route(
            "/compliance-url",
            self.get_compliance_url,
            methods=["GET"],
            response_model=ResponseModel[str],
        )
        self.router.add_api_route(
            "/policy-violations",
            self.get_policy_violations,
            methods=["GET"],
            response_model=ResponseModel[List[PolicyViolation]],
        )
        self.router.add_api_route(
            "/images",
            self.get_images,
            methods=["GET"],
            response_model=ResponseModel[List[Image]],
        )
        self.router.add_api_route(
            "/deployments",
            self.get_deployments,
            methods=["GET"],
            response_model=ResponseModel[List[Deployment]],
        )
        self.router.add_api_route(
            "/secrets",
            self.get_secrets,
            methods=["GET"],
            response_model=ResponseModel[List[Secret]],
        )
        self.router.add_api_route(
            "/get-debug-levels", self.get_debug_levels, methods=["GET"]
        )
        self.router.add_api_route(
            "/enable-debug", self.get_enable_debug, methods=["GET"]
        )
        self.router.add_api_route(
            "/disable-debug", self.get_disable_debug, methods=["GET"]
        )
        self._activated = activated

    @function_logger_factory(logger)
    def set_activated(self, activated: bool):
        logger.debug(f"Set route active: {activated}")
        self._activated = activated

    @function_logger_factory(logger)
    def set_endpoints(self, ui_url: str, api_endpoints: List[ProviderAPIEndpoints]):
        logger.debug(f"setting endpoints, ui url: {ui_url}, others: {api_endpoints}")
        self.__ui_url = ui_url
        self.__stackrox_api = StackRoxAPIWrapper(
            self.__stackrox_authentication, api_endpoints
        )

    @function_logger_factory(logger)
    def enable_oidc(self):
        # https+insecure://vm-128-206.cloud.dkfz-heidelberg.de/auth/realms/kaapana
        # {"id":"","name":"Kaapana","type":"oidc","config":{"mode":"auto","do_not_use_client_secret":"false","client_secret":"","client_id":"kaapana","issuer":"https+insecure://vm-128-206.cloud.dkfz-heidelberg.de/auth/realms/kaapana"},"uiEndpoint":"vm-128-206.cloud.dkfz-heidelberg.de:19443","enabled":true,"traits":{"mutabilityMode":"ALLOW_MUTATE"}}
        pass

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_stackrox_url(self):
        if self.__ui_url is not None and self.__ui_url != "":
            return {"data": self.__ui_url}
        else:
            raise HTTPException(
                status_code=HTTP_404_NOT_FOUND, detail="Url not available"
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_network_graph_url(self):
        try:
            return {"data": self.__stackrox_api.get_network_graph_url(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox network graph url",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_compliance_url(self):
        try:
            return {"data": self.__stackrox_api.get_compliance_url(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox compliance url",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_policy_violations(self):
        try:
            return {"data": self.__stackrox_api.get_policy_violations(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox policy violations",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_images(self):
        try:
            return {"data": self.__stackrox_api.get_images(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox image information",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_deployments(self):
        try:
            return {"data": self.__stackrox_api.get_deployments(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox deployment information",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_secrets(self):
        try:
            return {"data": self.__stackrox_api.get_secrets(self.__ui_url)}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox secret information",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_debug_levels(self):
        try:
            return {"data": self.__stackrox_api.get_debug_levels()}
        except:
            raise HTTPException(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not retrieve StackRox debug levels",
            )

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_enable_debug(self):
        self.__stackrox_api.enable_debug()

    @DeactivatableRouter.activation_wrapper
    @function_logger_factory(logger)
    def get_disable_debug(self):
        self.__stackrox_api.disable_debug()
