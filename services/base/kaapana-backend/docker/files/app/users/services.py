from keycloak import KeycloakAdmin
from typing import List
from keycloak.exceptions import KeycloakGetError
from .schemas import KaapanaUser, KaapanaGroup, KaapanaRole


class UserService:
    def __init__(
        self,
        server_url: str,
        client_secret: str,
        realm_name: str = "kaapana",
        verify: bool = False,
    ):
        self.server_url = server_url
        self.client_secret = client_secret
        self.realm_name = realm_name
        self.verify = verify
        self._login()

    def _login(self):
        self.keycloak_admin = KeycloakAdmin(
            server_url=self.server_url,
            client_id="kaapana-service",
            client_secret_key=self.client_secret,
            realm_name=self.realm_name,
            user_realm_name=self.realm_name,
            verify=self.verify,
        )

    def get_users(
        self, username: str = None, group_id: str = None
    ) -> List[KaapanaUser]:
        self._login()
        if username:
            lower_user_name = username.lower()
            result = self.keycloak_admin.get_users(query={"search": lower_user_name})
        elif group_id:
            result = self.keycloak_admin.get_group_members(group_id)
        else:
            result = self.keycloak_admin.get_users({})
        return [KaapanaUser(name=r["username"], idx=r["id"]) for r in result]

    def get_user(self, idx: str) -> KaapanaUser:
        self._login()
        try:
            r = self.keycloak_admin.get_user(idx)
        except KeycloakGetError as e:
            return None
        return KaapanaUser(name=r["username"], idx=r["id"])

    def get_groups(self, user_id: str = None) -> List[KaapanaGroup]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_user_groups(user_id)
        else:
            result = self.keycloak_admin.get_groups()

        return [KaapanaGroup(name=r["name"], idx=r["id"]) for r in result]

    def get_group(self, idx: str = None) -> KaapanaGroup:
        self._login()
        try:
            r = self.keycloak_admin.get_group(group_id=idx)
        except KeycloakGetError:
            # Group not found
            return None
        return KaapanaGroup(name=r["name"], idx=r["id"])

    def _refresh_token_if_necessary(self):
        pass

    def get_roles(self, user_id: str = None) -> List[KaapanaRole]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_realm_roles_of_user(user_id)
        else:
            result = self.keycloak_admin.get_realm_roles()
        return [
            KaapanaRole(
                idx=r["id"], name=r["name"], description=r.get("description", "")
            )
            for r in result
        ]
