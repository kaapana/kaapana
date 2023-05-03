import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)


class KeycloakHelper():
    """
    Use this class to make authorized request to the keycloak REST API.
    The base api endpoint is based on KEYCLOAK environment variables.
    """
    def __init__(self):
        self.KEYCLOAK_USER = os.environ["KEYCLOAK_USER"]
        self.KEYCLOAK_PASSWORD = os.environ["KEYCLOAK_PASSWORD"]
        self.KEYCLOAK_HOST = os.environ["KEYCLOAK_HOST"]
        self.auth_url = f"https://{self.KEYCLOAK_HOST}/auth/admin/realms/"
        self.master_access_token = self.get_access_token(self.KEYCLOAK_USER, self.KEYCLOAK_PASSWORD, "https", self.KEYCLOAK_HOST, 443, False, "admin-cli")

    def get_access_token(self,
            username: str, 
            password: str, 
            protocol: str, 
            host: str, 
            port: int, 
            ssl_check: bool, 
            client_id: str, 
            realm: str = "master", 
            client_secret: str = None):

        payload = {
            'username': username,
            'password': password,
            'client_id': client_id,
            'grant_type': 'password'
        }
        if client_secret:
            payload['client_secret']= client_secret
        
        url = f'{protocol}://{host}:{port}/auth/realms/{realm}/protocol/openid-connect/token'
        r = requests.post(url, verify=ssl_check, data=payload)
        r.raise_for_status()
        access_token = r.json()['access_token']
        return access_token


    def make_authorized_request(self, url: str, request=requests.post, payload={}, update_url="", timeout=2, **kwargs):
        """
        Make an authorized request to the keycloak api using the access token stored in self.master_access_token
        """
        for key, val in kwargs.items():
            payload[key] = val
        logger.debug(f"Requesting endpoint: {url} with method {request}")
        r = request(url,
            verify = False,
            json = payload,
            headers = {"Authorization": f"Bearer {self.master_access_token}"},
            timeout = timeout)

        if r.status_code in [409]:
            logger.warning("Ressource already exists.")
            if update_url:
                logger.info(f"Ressource will be updated!")
                r = self.make_authorized_request(update_url, requests.put, payload, timeout=timeout, **kwargs)
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
        r = self.make_authorized_request(url, requests.post, payload=payload, update_url=update_url, timeout=120, **kwargs)
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
        return self.make_authorized_request(url, requests.post, payload=payload, update_url=update_url, **kwargs)

    def get_realm_roles(self):
        url = self.auth_url +"kaapana/roles"
        return self.make_authorized_request(url, requests.get)

    def post_role_mapping(self, roles_to_add: list, group: str):
        group_id = self.get_group_id(group)
        payload = []
        roles = self.get_realm_roles().json()
        for role in roles:
            if role["name"] in roles_to_add:
                payload.append(role)
        url = self.auth_url + f"kaapana/groups/{group_id}/role-mappings/realm"
        return self.make_authorized_request(url, requests.post, payload)

    def post_user(self, payload, **kwargs):
        url = self.auth_url + "kaapana/users"
        return self.make_authorized_request(url, requests.post, payload, **kwargs)

    def get_client_id(self, client_name: str):
        all_clients = self.make_authorized_request(self.auth_url + f"kaapana/clients", requests.get).json()
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
        return self.make_authorized_request(url, requests.post, payload=payload, update_url=update_url ,**kwargs)