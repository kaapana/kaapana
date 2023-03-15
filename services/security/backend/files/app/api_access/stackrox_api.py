from functools import wraps
import inspect
from typing import List, Optional
import uuid
import httpx
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory, trimContent
from models.JWTToken import JWTToken
import jwt
from datetime import datetime, timezone

from models.provider import ProviderAPIEndpoints
from models.stackrox_models import (
    AlertDeployment,
    CommonEntityInfo,
    Deployment,
    Image,
    Policy,
    PolicyViolation,
    Secret,
)

logger = get_logger(f"{LOGGER_NAME}.stackrox_api", logging.INFO)

STACKROX_API_ITEM_LIMIT = 100


class StackRoxAPIAuthentication:
    __jwt_token: JWTToken = None
    __api_username: str = "admin"
    __api_pw: str = "gtSXi9UWsosv3aTQ6jVn4Ag6Y"
    __api_endpoint: Optional[str] = None

    def __init__(self):
        self.__read_credentials()

    def __read_credentials(self):
        pass
        # user_file = "/api_credentials/wazuh_username"
        # pw_file = "/api_credentials/wazuh_password"

        # if os.path.isfile(user_file) and self.__api_username == "":
        #     with open(user_file, "r") as file:
        #         self.__api_username = file.read().rstrip()

        # if os.path.isfile(pw_file) and self.__api_pw == "":
        #     with open(pw_file, "r") as file:
        #         self.__api_pw = file.read().rstrip()

        # logger.debug(f"wazuh user: {self.__api_username}, pw: {self.__api_pw}")

    @function_logger_factory(logger)
    def __retrieve_token(self, retry=True) -> bool:
        self.__read_credentials()

        try:
            available_authproviders_result = httpx.get(
                f"{self.__api_endpoint}/v1/login/authproviders", verify=False
            )

            available_authproviders_result.raise_for_status()

            # id of basic login authprovider has to be state data of next request
            logger.info(available_authproviders_result.json())
            state = available_authproviders_result.json()["authProviders"][0]["id"]

            headers = {"Content-Type": "application/json"}
            data = {
                "externalToken": f"username={self.__api_username}&password={self.__api_pw}",
                "state": state,
                "type": "basic",
            }
            result = httpx.post(
                f"{self.__api_endpoint}/v1/authProviders/exchangeToken",
                verify=False,
                headers=headers,
                json=data,
            )
            logger.debug(
                f"result from '/v1/authProviders/exchangeToken': {result} - {trimContent(result.content)}"
            )

            if result.status_code == 401 and retry:
                return self.__retrieve_token(False)

            result.raise_for_status()

            jwt_token = result.json()["token"]
            decoded_token = jwt.decode(
                jwt_token, verify=False, options={"verify_signature": False}
            )
            expiration_date = datetime.fromtimestamp(
                float(decoded_token["exp"]), tz=timezone.utc
            )
            self.__jwt_token = JWTToken(
                token=jwt_token, expiration_date=expiration_date
            )

            return True
        except Exception as e:
            logger.info(f"exception while retrieving token: {e}")
            return False

    @function_logger_factory(logger)
    def get_bearer_token(self) -> Optional[str]:
        if (
            self.__jwt_token is None
            or self.__jwt_token.expired_or_expires_soon(expires_soon_seconds=30)
        ) and not self.__retrieve_token():
            logger.error("Could not retrieve StackRox jwt token")
            return None

        logger.debug(f"StackRox jwt token available")
        return f"Bearer {self.__jwt_token.token}"

    @function_logger_factory(logger)
    def reset(self):
        self.__jwt_token = None
        self.__api_username = ""
        self.__api_pw = ""

    def set_api_endpoint(self, api_endpoint: str):
        self.__api_endpoint = api_endpoint


class StackRoxAPIWrapper:
    __stackrox_authentication: StackRoxAPIAuthentication

    def __init__(
        self,
        stackrox_authentication: StackRoxAPIAuthentication,
        api_endpoints: List[ProviderAPIEndpoints],
    ):
        self.__stackrox_authentication = stackrox_authentication

        logger.debug(f"stackrox api given endpoints: {api_endpoints}")
        api = list(filter(lambda endpoint: endpoint.identifier == "api", api_endpoints))
        self.__api_endpoint = (
            api[0].endpoint.removesuffix("/")
            if len(api) > 0
            else "https://security-stackrox-service.stackrox.svc:443"
        )
        self.__stackrox_authentication.set_api_endpoint(self.__api_endpoint)
        logger.debug(
            f"setting stackrox api wrapper endpoints, api: {self.__api_endpoint}"
        )

    # todo extract here and in wazuh api
    def retry_on_unauthorized(fn):
        if inspect.iscoroutinefunction(fn):

            @wraps(fn)
            async def wrapper(self, *args, **kwargs):
                try:
                    logger.debug("retry_wrapper calling function")
                    return await fn(self, *args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        logger.debug("retry_wrapper 401, retrying")
                        # retry once with newly read credentials
                        self.__stackrox_authentication.reset()
                        return await fn(self, *args, **kwargs)

            return wrapper
        else:

            @wraps(fn)
            def wrapper(self, *args, **kwargs):
                try:
                    logger.debug("retry_wrapper calling function")
                    return fn(self, *args, **kwargs)
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 401:
                        logger.debug("retry_wrapper 401, retrying")
                        # retry once with newly read credentials
                        self.__stackrox_authentication.reset()
                        return fn(self, *args, **kwargs)

            return wrapper

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_network_graph_url(self, ui_url: str) -> str:
        return f"{ui_url}/main/network-graph"

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_compliance_url(self, ui_url: str) -> str:
        return f"{ui_url}/main/compliance"

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_policy_violations(self, ui_url: str) -> List[PolicyViolation]:
        policy_violation_list: List[PolicyViolation] = []
        iteration = 0

        while True:
            params = {
                "pagination.limit": STACKROX_API_ITEM_LIMIT,
                "pagination.offset": iteration * STACKROX_API_ITEM_LIMIT,
                "pagination.sortOption.field": "Severity",
                "pagination.sortOption.reversed": "true",
            }

            result = httpx.get(
                f"{self.__api_endpoint}/v1/alerts",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/alerts': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            affected_items = result.json()["alerts"]

            for item in affected_items:
                deployment = AlertDeployment(
                    name=item["deployment"]["name"],
                    inactive=item["deployment"]["inactive"],
                )
                policy = Policy(
                    id=item["policy"]["id"],
                    name=item["policy"]["name"],
                    severity=item["policy"]["severity"].replace("_SEVERITY", ""),
                    description=item["policy"]["description"],
                    categories=item["policy"]["categories"],
                )
                commonEntityInfo = CommonEntityInfo(
                    clusterName=item["commonEntityInfo"]["clusterName"],
                    namespace=item["commonEntityInfo"]["namespace"],
                    resourceType=item["commonEntityInfo"]["resourceType"],
                )

                # url = /main/violations/d1dd2a31-594c-43e8-abea-c66998ccfc73
                policy_violation = PolicyViolation(
                    id=item["id"],
                    lifecycleStage=item["lifecycleStage"],
                    time=item["time"],
                    state=item["state"],
                    commonEntityInfo=commonEntityInfo,
                    deployment=deployment,
                    policy=policy,
                    externalUrl=f"{ui_url}/main/violations/{item['id']}",
                )
                policy_violation_list += [policy_violation]

            iteration += 1

            # if we have STACKROX_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < STACKROX_API_ITEM_LIMIT:
                break

        return policy_violation_list

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_images(self, ui_url: str) -> List[Image]:
        image_id_list = []
        iteration = 0

        while True:
            params = {
                "pagination.limit": STACKROX_API_ITEM_LIMIT,
                "pagination.offset": iteration * STACKROX_API_ITEM_LIMIT,
                # "pagination.sortOption.field": "Priority",
                # "pagination.sortOption.reversed": "true",
            }

            result = httpx.get(
                f"{self.__api_endpoint}/v1/images",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/alerts': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            affected_items = result.json()["images"]

            for item in affected_items:
                image_id_list += [{"id": item["id"], "priority": item["priority"]}]

            iteration += 1

            # if we have STACKROX_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < STACKROX_API_ITEM_LIMIT:
                break

        image_id_list.sort(key=lambda x: int(x["priority"]))

        image_list: List[Image] = []
        for image in image_id_list:
            image_id = image["id"]

            params = {"stripDescription": True}

            result = httpx.get(
                f"{self.__api_endpoint}/v1/images/{image_id}",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/images/{image_id}': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            image = result.json()
            image_list += [
                Image(
                    id=image["id"],
                    name=image["name"]["fullName"],
                    registry=image["name"]["registry"],
                    os=image["scan"]["operatingSystem"]
                    if "scan" in image and image["scan"] is not None
                    else None,
                    cves=image["cves"] if "cves" in image else None,
                    fixableCves=image["fixableCves"]
                    if "fixableCves" in image
                    else None,
                    priority=image["priority"],
                    riskScore=image["riskScore"],
                    topCvss=image["topCvss"] if "topCvss" in image else None,
                    externalUrl=f"{ui_url}/main/vulnerability-management/image/{image['id']}",
                )
            ]

        return image_list

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_deployments(self, ui_url: str) -> List[Deployment]:
        deployment_id_list = []
        iteration = 0

        while True:
            params = {
                "pagination.limit": STACKROX_API_ITEM_LIMIT,
                "pagination.offset": iteration * STACKROX_API_ITEM_LIMIT,
            }

            result = httpx.get(
                f"{self.__api_endpoint}/v1/deployments",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/deployments': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            affected_items = result.json()["deployments"]

            for item in affected_items:
                deployment_id_list += [{"id": item["id"], "priority": item["priority"]}]

            iteration += 1

            # if we have STACKROX_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < STACKROX_API_ITEM_LIMIT:
                break

        deployment_id_list.sort(key=lambda x: int(x["priority"]))

        deployment_list: List[Deployment] = []
        for deployment in deployment_id_list:
            deployment_id = deployment["id"]

            result = httpx.get(
                f"{self.__api_endpoint}/v1/deployments/{deployment_id}",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/deployments/{deployment_id}': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            deployment = result.json()

            deployment_list += [
                Deployment(
                    id=deployment["id"],
                    name=deployment["name"],
                    namespace=deployment["namespace"],
                    priority=deployment["priority"],
                    riskScore=deployment["riskScore"],
                    externalUrl=f"{ui_url}/main/vulnerability-management/deployment/{deployment['id']}",
                )
            ]

        return deployment_list

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def get_secrets(self, ui_url: str) -> List[Secret]:
        secret_id_list = []
        iteration = 0

        while True:
            params = {
                "pagination.limit": STACKROX_API_ITEM_LIMIT,
                "pagination.offset": iteration * STACKROX_API_ITEM_LIMIT,
            }

            result = httpx.get(
                f"{self.__api_endpoint}/v1/secrets",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/secrets': {result} - {trimContent(result.content)}"
            )

            result.raise_for_status()

            affected_items = result.json()["secrets"]

            for item in affected_items:
                secret_id_list += [{"id": item["id"], "name": item["name"]}]

            iteration += 1

            # if we have STACKROX_API_ITEM_LIMIT items, there could potentially be more -> query once more
            if len(affected_items) < STACKROX_API_ITEM_LIMIT:
                break

        secret_id_list.sort(key=lambda x: x["name"])

        secret_list: List[Secret] = []
        for secret in secret_id_list:
            secret_id = secret["id"]

            result = httpx.get(
                f"{self.__api_endpoint}/v1/secrets/{secret_id}",
                params=params,
                verify=False,
                headers={
                    "Authorization": self.__stackrox_authentication.get_bearer_token()
                },
            )
            logger.debug(
                f"result from '/v1/secrets/{secret_id}': {result} - {(result.content)}"  # todo: trim content
            )

            result.raise_for_status()

            secret = result.json()

            container_relationships = (
                secret["relationship"]["containerRelationships"]
                if "relationship" in secret
                else []
            )
            deployment_relationships = (
                secret["relationship"]["deploymentRelationships"]
                if "relationship" in secret
                else []
            )

            secret_list += [
                Secret(
                    id=secret["id"],
                    name=secret["name"],
                    namespace=secret["namespace"],
                    type=secret["type"],
                    createdAt=secret["createdAt"],
                    containers=container_relationships,
                    deployments=deployment_relationships,
                    externalUrl=f"{ui_url}/main/configmanagement/secret/{secret['id']}",
                )
            ]

        return secret_list
