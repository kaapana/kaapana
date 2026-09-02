import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from kaapanapy.logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)


class KeycloakHelper:
    """
    Use this class to make authorized request to the keycloak REST API.
    The base api endpoint is based on KEYCLOAK environment variables.
    """

    def __init__(
        self,
        client_secret=None,
        keycloak_host=None,
        keycloak_https_port=None,
    ):
        self.client_secret = (
            client_secret or os.environ["KEYCLOAK_SERVICE_CLIENT_SECRET"]
        )
        self.keycloak_host = keycloak_host or os.environ["KEYCLOAK_HOST"]
        self.keycloak_https_port = keycloak_https_port or os.getenv(
            "KEYCLOAK_HTTPS_PORT", 443
        )
        self.auth_url = f"https://{self.keycloak_host}:{self.keycloak_https_port}/auth/admin/realms/"
        self.service_access_token = self.get_access_token(
            self.client_secret,
            "https",
            self.keycloak_host,
            self.keycloak_https_port,
            False,
        )

    def get_access_token(
        self,
        client_secret: str,
        protocol: str,
        host: str,
        port: int,
        ssl_check: bool,
        realm: str = "kaapana",
    ):
        payload = {
            "client_id": "kaapana-service",
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        }
        url = f"{protocol}://{host}:{port}/auth/realms/{realm}/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        r.raise_for_status()
        return r.json()["access_token"]

    def make_authorized_request(
        self,
        url: str,
        request=requests.post,
        payload={},
        update_url="",
        # 30s rather than 2s: while Keycloak is still coming up after a deploy, or waits
        # on a slow LDAP federation, admin API calls take longer than 2s and the setup
        # jobs failed spuriously.
        timeout=30,
        **kwargs,
    ):
        """
        Make an authorized request to the keycloak api using the access token stored in self.service_access_token
        """
        for key, val in kwargs.items():
            payload[key] = val
        logger.debug(f"Requesting endpoint: {url} with method {request}")
        r = request(
            url,
            verify=False,
            json=payload,
            headers={"Authorization": f"Bearer {self.service_access_token}"},
            timeout=timeout,
        )

        if r.status_code in [409]:
            logger.warning("Ressource already exists.")
            if update_url:
                logger.info(f"Ressource will be updated!")
                r = self.make_authorized_request(
                    update_url, requests.put, payload, timeout=timeout, **kwargs
                )
                logger.info(f"Ressource was updated!")
                r.raise_for_status()
            else:
                logger.warning(f"Ressource won't be updated")
        else:
            r.raise_for_status()
        return r

    def post_user(self, payload, reset_password=False, **kwargs):
        url = self.auth_url + "kaapana/users"
        response = self.make_authorized_request(url, requests.post, payload, **kwargs)
        if response.status_code == 409 and reset_password:
            logger.warning(f"Reset password!")
            user = self.get_user_by_name(payload.get("username"))
            user_id = user.get("id")
            url = self.auth_url + f"kaapana/users/{user_id}/reset-password"
            reset_payload = payload.get("credentials")[0]
            reset_payload["temporary"] = False
            reset_response = self.make_authorized_request(
                url, requests.put, reset_payload, **kwargs
            )
            reset_response.raise_for_status()
            logger.info(f"Reset password for user {user_id} ")

    def get_user_by_name(self, username: str):
        """
        Get the user representation by the username
        """
        url = self.auth_url + f"kaapana/users?username={username}"
        r = self.make_authorized_request(url, requests.get)
        return r.json()[0]
