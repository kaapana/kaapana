import os
import requests
import json
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

class KeycloakHelper():

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


    def __configure_keycloak(self, url: str, request = requests.post, payload = {}, **kwargs):
        for key, val in kwargs.items():
            payload[key] = val
        r = request(url,
            verify = False,
            json = payload,
            headers= {"Authorization": f"Bearer {self.master_access_token}"}
            )
            
        try: 
            assert r.status_code < 400
        except AssertionError:
            if r.status_code in [409]:
                print("Ressource already exists.")
            else:
                print(r.text)
                r.raise_for_status()
        return r

    def post_realm(self, file, **kwargs):
        url = self.auth_url
        payload = json.load(open(file,"r"))
        self.__configure_keycloak(url, requests.post, payload, **kwargs)
    
    def post_group(self, file, **kwargs):
        url = self.auth_url + "kaapana/groups"
        payload = json.load(open(file,"r"))
        self.__configure_keycloak(url, requests.post, payload, **kwargs)
    
    def get_groups(self):
        url = self.auth_url + "kaapana/groups"
        self.__configure_keycloak(url, requests.get)

    def post_role_mapping(self, file, group):
        url = self.auth_url + "kaapana/groups"
        r = self.__configure_keycloak(url, requests.get)
        group_id = None
        for found_group in r.json():
            if found_group["name"] == group:
                group_id = found_group["id"]
                break
        
        if not group_id:
            print(f"Group with name: {group} not found!")
            print("Found the folling groups:")
            print(r.json())
            return None

        payload = json.load(open(file,"r"))["realmMappings"]
        print(self.auth_url)
        url = self.auth_url + f"kaapana/groups/{group_id}/role-mappings/realm"
        r = self.__configure_keycloak(url, requests.post, payload)

    def post_user(self, file, **kwargs):
        url = self.auth_url + "kaapana/users"
        payload = json.load(open(file,"r"))
        self.__configure_keycloak(url, requests.post, payload, **kwargs)

    def post_client(self, file, **kwargs):
        url = self.auth_url + "kaapana/clients"
        payload = json.load(open(file,"r"))
        r = self.__configure_keycloak(url, requests.post, payload, **kwargs)


if __name__=='__main__':
    keycloak = KeycloakHelper()
    
    ### Add realm
    file = "realm_objects/kaapana-realm.json"
    keycloak.post_realm(file)

    ### Add group
    file = "realm_objects/group-all_data.json"
    keycloak.post_group(file)
    keycloak.get_groups()

    ### Add role mappings to group
    file = "realm_objects/role-mappings.json"
    keycloak.post_role_mapping(file, "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    keycloak.post_user(file)

    ### Add client 
    file = "realm_objects/kaapana-client.json"
    host = os.environ["HOSTNAME"]
    keycloak.post_client(file, redirectUris=[ "/oauth2/callback", f"https://{host}:443/minio-console/oauth_callback/" ])


