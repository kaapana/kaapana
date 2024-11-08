import os
import re

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
import logging

from kaapanapy.logger import get_logger

logger = get_logger(__name__, logging.DEBUG)


def get_keycloak_helper():
    """
    Get an instance of the KeycloakHelper class
    """
    kc_client = KeycloakHelper()
    return kc_client


# Utility function to convert a dictionary from camelCase key to snake_case key
def dict_keys_camel_to_snake(data: dict):
    def camel_to_snake_str(name):
        return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()

    return {camel_to_snake_str(key): value for key, value in data.items()}


# Utility function to convert a list of dictionaries, with keys from camelCase key to snake_case key
def list_of_dict_camel_to_snake(data: list):
    return [dict_keys_camel_to_snake(item) for item in data]


class KeycloakHelper:
    """
    Use this class to make authorized request to the keycloak REST API.
    The base api endpoint is based on KEYCLOAK environment variables.
    """

    def __init__(
        self,
        keycloak_user=None,
        keycloak_password=None,
        keycloak_host=None,
        keycloak_https_port=None,
    ):
        self.keycloak_user = keycloak_user or os.environ["KEYCLOAK_USER"]
        self.keycloak_password = keycloak_password or os.environ["KEYCLOAK_PASSWORD"]
        self.keycloak_host = keycloak_host or os.environ["KEYCLOAK_HOST"]
        self.keycloak_https_port = keycloak_https_port or os.getenv(
            "KEYCLOAK_HTTPS_PORT", 443
        )
        self.auth_url = f"https://{self.keycloak_host}:{self.keycloak_https_port}/auth/admin/realms/"
        self.master_access_token = self.get_access_token(
            self.keycloak_user,
            self.keycloak_password,
            "https",
            self.keycloak_host,
            self.keycloak_https_port,
            False,
            "admin-cli",
        )

    def get_access_token(
        self,
        username: str,
        password: str,
        protocol: str,
        host: str,
        port: int,
        ssl_check: bool,
        client_id: str,
        realm: str = "master",
        client_secret: str = None,
    ):
        payload = {
            "username": username,
            "password": password,
            "client_id": client_id,
            "grant_type": "password",
        }
        if client_secret:
            payload["client_secret"] = client_secret

        url = f"{protocol}://{host}:{port}/auth/realms/{realm}/protocol/openid-connect/token"
        r = requests.post(url, verify=ssl_check, data=payload)
        r.raise_for_status()
        access_token = r.json()["access_token"]
        return access_token

    def make_authorized_request(
        self,
        url: str,
        request=requests.post,
        payload={},
        update_url="",
        timeout=2,
        **kwargs,
    ):
        """
        Make an authorized request to the keycloak api using the access token stored in self.master_access_token
        """
        for key, val in kwargs.items():
            payload[key] = val

        logger.debug(f"Requesting endpoint: {url} with method {request}")
        r = request(
            url,
            verify=False,
            json=payload,
            headers={"Authorization": f"Bearer {self.master_access_token}"},
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

    def get_users(self):
        """
        Get all the keycloak users
        """
        url = self.auth_url + f"kaapana/users"
        r = self.make_authorized_request(url, requests.get)
        users_dict = list_of_dict_camel_to_snake(r.json())
        return users_dict

    def get_user_groups(self, userid: str):
        """
        Get keycloak user groups by userid
        """
        groups_url = self.auth_url + f"kaapana/users/{userid}/groups"
        try:
            groups_response = self.make_authorized_request(groups_url, requests.get)
            user_groups = [group["name"] for group in groups_response.json()]
            return user_groups
        except Exception as e:
            return []

    def get_user_by_name(self, username: str):
        """
        Get the user representation by the username
        """
        url = self.auth_url + f"kaapana/users?username={username}&exact=true"
        r = self.make_authorized_request(url, requests.get)

        response = r.json()
        if len(response) == 0:
            return None

        user_data = dict_keys_camel_to_snake(r.json()[0])
        user_data["groups"] = self.get_user_groups(user_data["id"])
        return user_data

    def get_user_by_id(self, userid: str):
        """
        Get the user representation by the keycloak id
        """
        url = self.auth_url + f"kaapana/users/{userid}"
        try:
            user_response = self.make_authorized_request(url, requests.get)
            user_data = dict_keys_camel_to_snake(user_response.json())
        except Exception as e:
            return None

        user_data["groups"] = self.get_user_groups(userid)
        return user_data
