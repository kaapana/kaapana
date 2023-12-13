import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)


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

    def post_realm(self, payload, update=True, **kwargs):
        url = self.auth_url
        realm = payload["id"]
        update_url = url + realm if update else ""
        r = self.make_authorized_request(
            url,
            requests.post,
            payload=payload,
            update_url=update_url,
            timeout=120,
            **kwargs,
        )
        return r

    def get_all_groups(self):
        url = self.auth_url + "kaapana/groups"
        return self.make_authorized_request(url, requests.get)

    def get_group_id(self, group: str):
        r = self.get_all_groups()
        group_id = None
        for found_group in r.json():
            if found_group["name"] == group:
                group_id = found_group["id"]
                return group_id
        if not group_id:
            logger.debug(f"Group with name: {group} not found!")
            logger.debug(f"Found the following groups: {r.json()}")
            return None

    def post_group(self, payload, update=True, **kwargs):
        url = self.auth_url + "kaapana/groups"
        group = payload["name"]
        group_id = self.get_group_id(group)
        update_url = url + f"/{group_id}" if update and group_id and group_id else ""
        return self.make_authorized_request(
            url, requests.post, payload=payload, update_url=update_url, **kwargs
        )

    def get_realm_roles(self):
        url = self.auth_url + "kaapana/roles"
        return self.make_authorized_request(url, requests.get)

    def post_role_mapping(
        self, roles_to_add: list, group: str = None, user: str = None
    ):
        assert group or user
        if group:
            group_id = self.get_group_id(group)
            url = self.auth_url + f"kaapana/groups/{group_id}/role-mappings/realm"
        elif user:
            user_id = self.get_user_by_name(user).get("id")
            url = self.auth_url + f"kaapana/users/{user_id}/role-mappings/realm"
        payload = []
        roles = self.get_realm_roles().json()
        for role in roles:
            if role["name"] in roles_to_add:
                payload.append(role)
        return self.make_authorized_request(url, requests.post, payload)

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

    def get_client_id(self, client_name: str):
        all_clients = self.make_authorized_request(
            self.auth_url + f"kaapana/clients", requests.get
        ).json()
        for client in all_clients:
            if client["clientId"] == client_name:
                id = client["id"]
                return id
        return None

    def get_client(self, client_name: str):
        id = self.get_client_id(client_name)
        url = self.auth_url + f"kaapana/clients/{id}"
        return self.make_authorized_request(url, requests.get)

    def post_client(self, payload, update=True, **kwargs):
        url = self.auth_url + "kaapana/clients"
        client_name = payload["clientId"]
        client_id = self.get_client_id(client_name)
        update_url = url + f"/{client_id}" if update and client_id else ""
        return self.make_authorized_request(
            url, requests.post, payload=payload, update_url=update_url, **kwargs
        )

    def post_composite_role(self, composite_role: str, roles_to_add: list):
        roles = self.get_realm_roles().json()
        role_id = [
            available_role.get("id")
            for available_role in roles
            if available_role.get("name") == composite_role
        ][0]

        payload = [
            role_to_add
            for role_to_add in roles
            if role_to_add.get("name") in roles_to_add
        ]

        url = self.auth_url + f"kaapana/roles-by-id/{role_id}/composites"
        return self.make_authorized_request(url, requests.post, payload)

    def get_composite_role(self, role):
        roles = self.get_realm_roles().json()
        role_id = [
            available_role.get("id")
            for available_role in roles
            if available_role.get("name") == role
        ][0]
        url = self.auth_url + f"kaapana/roles-by-id/{role_id}/composites"
        return self.make_authorized_request(url, requests.get)

    def post_client_role_mapping(self, client: str, client_role: str, username: str):
        """
        Post a role mapping for a client role
        client: the client of the role
        client_role: the name of the role
        username: Name of the user
        """
        client_id = self.get_client_id(client)
        role_representation = self.get_client_role(client_id, client_role)
        user_id = self.get_user_by_name(username).get("id")
        url = (
            self.auth_url + f"kaapana/users/{user_id}/role-mappings/clients/{client_id}"
        )
        return self.make_authorized_request(url, requests.post, [role_representation])

    def get_client_role(self, client_id: str, client_role: str):
        """
        Get the role represenation of a client role
        client_id: the id of the client the role belongs to (not the name)
        client_role: the name of the client
        """
        url = self.auth_url + f"kaapana/clients/{client_id}/roles"
        r = self.make_authorized_request(url, requests.get)
        client_roles = r.json()
        return [role for role in client_roles if role.get("name") == client_role][0]

    def get_user_by_name(self, username: str):
        """
        Get the user representation by the username
        """
        url = self.auth_url + f"kaapana/users?username={username}"
        r = self.make_authorized_request(url, requests.get)
        return r.json()[0]
