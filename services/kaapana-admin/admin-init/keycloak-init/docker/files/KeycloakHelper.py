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


    def make_authorized_request(self, url: str, request = requests.post, payload = {}, **kwargs):
        """
        Make an authorized request to the keycloak api using the access token stored in self.master_access_token
        """
        for key, val in kwargs.items():
            payload[key] = val
        r = request(url,
            verify = False,
            json = payload,
            headers = {"Authorization": f"Bearer {self.master_access_token}"},
            timeout = 2
            )

        if r.status_code in [409]:
            logger.warning("Ressource already exists.")
            logger.warning("Ressource not created.")
            logger.warning(r.text)
        else:
            logger.debug(f"Requesting endpoint: {url} with method {request}")
            r.raise_for_status()
        return r

    def post_realm(self, payload, **kwargs):
        url = self.auth_url
        return self.make_authorized_request(url, requests.post, payload, **kwargs)
    
    def post_group(self, payload, **kwargs):
        url = self.auth_url + "kaapana/groups"
        return self.make_authorized_request(url, requests.post, payload, **kwargs)
    
    def get_client(self, client_name: str):
        all_clients = self.make_authorized_request(self.auth_url + f"kaapana/clients", requests.get).json()
        for client in all_clients:
            if client["clientId"] == client_name:
                id = client["id"]
                break
        url = self.auth_url + f"kaapana/clients/{id}"
        return self.make_authorized_request(url, requests.get)

    def get_groups(self):
        url = self.auth_url + "kaapana/groups"
        return self.make_authorized_request(url, requests.get)

    def get_realm_roles(self):
        url = self.auth_url +"kaapana/roles"
        return self.make_authorized_request(url, requests.get)

    def post_role_mapping(self, roles_to_add: list, group: str):
        url = self.auth_url + "kaapana/groups"
        r = self.make_authorized_request(url, requests.get)
        group_id = None
        for found_group in r.json():
            if found_group["name"] == group:
                group_id = found_group["id"]
                break
        if not group_id:
            logger.debug(f"Group with name: {group} not found!")
            logger.debug("Found the folling groups:")
            logger.debug(r.json())
            return None

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

    def post_client(self, payload, **kwargs):
        url = self.auth_url + "kaapana/clients"
        return self.make_authorized_request(url, requests.post, payload, **kwargs)