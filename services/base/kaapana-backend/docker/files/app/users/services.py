from keycloak import KeycloakAdmin
from typing import List
from keycloak.exceptions import KeycloakGetError, KeycloakPostError
from .schemas import KaapanaUser, KaapanaGroup, KaapanaRole
from app.logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)


class UserService:
    def __init__(
        self,
        server_url: str,
        username: str,
        password: str,
        realm_name: str = "kaapana",
        user_realm_name: str = "master",
        verify: bool = False,
    ):
        self.server_url = server_url
        self.username = username
        self.password = password
        self.realm_name = realm_name
        self.user_realm_name = user_realm_name
        self.verify = verify
        self._login()

    def _login(self):
        # Option 1 - Use Admin from Master (insecure)
        # keycloak_admin = KeycloakAdmin(server_url="https://localhost/auth/", #server_url="https://localhost/auth/",
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
        self.keycloak_admin = KeycloakAdmin(
            server_url=self.server_url,
            username=self.username,
            password=self.password,
            realm_name=self.realm_name,
            user_realm_name=self.user_realm_name,
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
        return [
            KaapanaUser(
                name=r["username"],
                idx=r["id"],
                attributes=r.get("attributes", {}),
                email=r.get("email", ""),
                firstName=r.get("firstName", ""),
                lastName=r.get("lastName", ""),
            )
            for r in result
        ]

    def get_user(self, idx: str) -> KaapanaUser:
        self._login()
        try:
            r = self.keycloak_admin.get_user(idx)
        except KeycloakGetError as e:
            raise e
        return KaapanaUser(
            name=r["username"],
            idx=r["id"],
            attributes=r.get("attributes", []),
            email=r.get("email", ""),
            firstName=r.get("firstName", ""),
            lastName=r.get("lastName", ""),
        )

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

    def get_roles(self, user_id: str = None, group_id: str = None) -> List[KaapanaRole]:
        self._login()
        if user_id:
            result = self.keycloak_admin.get_realm_roles_of_user(user_id)
        elif group_id:
            result = self.keycloak_admin.get_group_realm_roles(group_id)
        else:
            result = self.keycloak_admin.get_realm_roles()
        return [
            KaapanaRole(
                idx=r["id"], name=r["name"], description=r.get("description", "")
            )
            for r in result
        ]

    def post_user(
        self,
        username: str,
        email: str = None,
        firstName: str = None,
        lastName: str = None,
        attributes: dict = {},
    ) -> KaapanaUser:
        self._login()
        try:
            new_user = self.keycloak_admin.create_user(
                {
                    "username": username,
                    "email": email,
                    "enabled": True,
                    "firstName": firstName,
                    "lastName": lastName,
                }
            )
        except KeycloakPostError as e:
            logger.warning(f"User exists with same {username=} or {email=}!")
            raise e

        logger.debug(f"{new_user=}")
        return KaapanaUser(
            idx=new_user,
            name=username,
            email=email,
            firstName=firstName,
            lastName=lastName,
            attributes=attributes,
        )

    def post_group(
        self,
        groupname: str,
    ) -> KaapanaGroup:
        self._login()
        try:
            new_group = self.keycloak_admin.create_group({"name": groupname})
        except KeycloakPostError as e:
            logger.warning(f"Group exists with same {groupname=}!")
            raise e

        logger.debug(f"{new_group=}")
        return KaapanaGroup(idx=new_group, name=groupname)

    def group_user_add(self, user_id: str, group_id: str) -> None:
        self._login()
        return self.keycloak_admin.group_user_add(user_id, group_id)

    def assign_realm_roles(self, user_id: str, roles: list) -> None:
        self._login()
        return self.keycloak_admin.assign_realm_roles(user_id, roles)
