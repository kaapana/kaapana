from typing import Optional
import httpx
import logging
from helpers.resources import LOGGER_NAME
from helpers.logger import get_logger, function_logger_factory
from models.JWTToken import JWTToken
import jwt
from datetime import datetime, timezone
import base64
import os
from functools import wraps

logger = get_logger(f"{LOGGER_NAME}.wazuh", logging.INFO)

class WazuhAPIAuthentication():
    __jwt_token: JWTToken = None
    __api_username: str = ""
    __api_pw: str = ""

    def __init__(self):
        self.__read_credentials()

    def __read_credentials(self):
        user_file = "/api_credentials/wazuh_username"
        pw_file = "/api_credentials/wazuh_password"
        
        if os.path.isfile(user_file) and self.__api_username == "":
            with open(user_file, "r") as file:
                self.__api_username = file.read().rstrip()
        
        if os.path.isfile(pw_file) and self.__api_pw == "":
            with open(pw_file, "r") as file:
                self.__api_pw = file.read().rstrip()

        logger.info(f"wazuh user: {self.__api_username}, pw: {self.__api_pw}")

    @function_logger_factory(logger)
    def __jwt_token_expired_or_expires_soon(self) -> bool:
        if self.__jwt_token is None:
            logger.debug("no jwt token saved")
            return True

        if self.__jwt_token.is_expired():
            logger.debug("jwt token is expired")
            return True

        if self.__jwt_token.get_seconds_until_expiration() < 30:
            logger.debug("expiration date of jwt token is in less than 30s")
            return True
        
        logger.debug("token does not expire in the next 30s")
        return False

    @function_logger_factory(logger)
    def __retrieve_token(self) -> bool:
        self.__read_credentials()
        auth_bytes = base64.b64encode(bytes(f"{self.__api_username}:{self.__api_pw}", "utf-8"))
        auth_base64 = auth_bytes.decode("utf-8")

        try:
            headers = {"Content-Type": "application/json", "Authorization":f"Basic {auth_base64}"} 
            result = httpx.get("https://security-wazuh-service.services.svc:55000/security/user/authenticate", verify=False, headers=headers)
            logger.debug(f"wazuh auth result: {result}")

            jwt_token = result.json()["data"]["token"]
            decoded_token = jwt.decode(jwt_token, verify=False, options={'verify_signature': False})
            expiration_date = datetime.fromtimestamp(float(decoded_token['exp']), tz=timezone.utc)
            self.__jwt_token = JWTToken(token=jwt_token, expiration_date=expiration_date)

            return True
        except Exception as e:
            logger.info(f"Expected exception while retrieving token: {e}")
            return False

    @function_logger_factory(logger)
    def get_bearer_token(self) -> Optional[str]:
        if self.__jwt_token_expired_or_expires_soon() and not self.__retrieve_token():
            logger.error("Could not retrieve Wazuh jwt token")
            return None

        logger.debug(f"Wazuh jwt token available")
        return f"Bearer {self.__jwt_token.token}"

    @function_logger_factory(logger)
    def reset(self):
        self.__jwt_token = None
        self.__api_username = ""
        self.__api_pw = ""

class WazuhAPIWrapper():
    __wazuh_authentication: WazuhAPIAuthentication

    def __init__(self, wazuh_authentication: WazuhAPIAuthentication):
        # todo: add api endpoint as init arg
        self.__wazuh_authentication = wazuh_authentication

    def retry_on_unauthorized(fn):
        @wraps(fn)
        def wrapper(self, *args, **kwargs):
            try:
                return fn(self, *args, **kwargs)
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    # retry once with newly read credentials
                    self.__wazuh_authentication.reset()
                    return fn(self, *args, **kwargs)

        return wrapper

    @retry_on_unauthorized
    @function_logger_factory(logger)
    def is_agent_installed(self) -> bool:
        result = httpx.get("https://security-wazuh-service.services.svc:55000/agents", verify=False, headers={"Authorization": self.__wazuh_authentication.get_bearer_token()})
        logger.debug(f"result from wazuh agent endpoint: {result}")

        result.raise_for_status()

        data = result.json()["data"]
        total_agents = int(data["total_affected_items"])
        logger.debug(f"result as json: {data}")
        logger.debug(f"total agents: {total_agents}")
        return total_agents > 1 # API lists manager instance as agent, but we need an additional agent running on host machine
