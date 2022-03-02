from keycloak import KeycloakAdmin
from typing import List
from keycloak.exceptions import KeycloakGetError
from app.schemas.users import KaapanaUser, KaapanaGroup, KaapanaRole

class UserService:
    def __init__(self, server_url: str,  username: str, password: str, realm_name : str = "kaapana", user_realm_name : str = "kaapana", verify: bool = False):
        self.server_url = server_url
        self.username = username
        self.password = password
        self.realm_name = realm_name
        self.user_realm_name = user_realm_name
        self.verify = verify
        self._login()

    def _login(self):
        # Option 1 - Use Admin from Master (insecure)
        #keycloak_admin = KeycloakAdmin(server_url="https://localhost/auth/", #server_url="https://localhost/auth/",
        #                               username='admin',
        #                               password='Kaapana2020',
        #                               realm_name="kaapana",
        #                               user_realm_name="master",
        #                               verify=False)
        #

        # Option 2 - Create a User in Kaapana for this
        # 
        # HowTo (Source: https://stackoverflow.com/questions/56743109/keycloak-create-admin-user-in-a-realm)
        # 1. Create a user and set a password
        # 2. Under Roles>Client Roles select `realm-managment` and add all roles `query-*` and `view-*`
        self.keycloak_admin = KeycloakAdmin(server_url=self.server_url,
                                       username=self.username,
                                       password=self.password,
                                       realm_name=self.realm_name,
                                       user_realm_name=self.user_realm_name,
                                       verify=self.verify)

    def get_users(self, username: str = None, group_id: str = None) -> List[KaapanaUser]:
        self._login()
        if username:
            lower_user_name = username.lower()
            result = self.keycloak_admin.get_users(query={"search": lower_user_name})
        elif group_id:
            result = self.keycloak_admin.get_group_members(group_id)
        else:
            result = self.keycloak_admin.get_users({})
        return [KaapanaUser(name=r['username'], idx=r['id']) for r in result]

    def get_user(self, idx: str) -> KaapanaUser:
        self._login()
        try:
          r = self.keycloak_admin.get_user(idx)
        except KeycloakGetError as e:
          return None
        return KaapanaUser(name=r['username'], idx=r['id'])

    def get_groups(self, user_id: str = None) -> List[KaapanaGroup]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_user_groups(user_id)
        else:
            result = self.keycloak_admin.get_groups()

        return [KaapanaGroup(name=r['name'], idx=r['id']) for r in result]

    def get_group(self, idx: str = None) -> KaapanaGroup:
        self._login()
        try:
            r = self.keycloak_admin.get_group(group_id=idx)
        except KeycloakGetError:
            # Group not found
            return None
        return KaapanaGroup(name=r['name'], idx=r['id'])

    def _refresh_token_if_necessary(self):
        pass

    def get_roles(self, user_id: str = None) -> List[KaapanaRole]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_realm_roles_of_user(user_id)
        else:
            result = self.keycloak_admin.get_realm_roles()
        return [KaapanaRole(idx=r['id'], name=r['name'], description=r.get('description', "")) for r in result]