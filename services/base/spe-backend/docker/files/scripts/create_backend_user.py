#!/usr/bin/env python3
import logging
import os
from typing import List
from keycloak import KeycloakAdmin

import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)


class KeycloakHelper:
    def __init__(
        self,
        server_url: str,
        kaapana_admin_user: str,
        kaapana_admin_passsword: str,
        kaapana_realm: str = "kaapana",
        verify: bool = False,
    ):
        self.keycloak_admin = KeycloakAdmin(
            server_url=server_url,
            username=kaapana_admin_user,
            password=kaapana_admin_passsword,
            realm_name=kaapana_realm,
            user_realm_name="master",
            verify=verify,
        )
        self.log = logging.getLogger(__name__)

    def user_id(self, username: str) -> str:
        """Checks if username exists and return its id or None otherwise"""
        users = self.keycloak_admin.get_users({"username": username})
        if len(users) > 0:
            user_id = users[0]["id"]
            self.log.info("Found user with name %s and id %s", username, user_id)
            return user_id
        else:
            self.log.info("Username %s not found", username)
            return None

    def create_user(self, username: str, password: str) -> str:
        """Creates a new user and returns it's id"""
        self.log.info("Creating new user with name %s", username)
        new_user_id = self.keycloak_admin.create_user(
            {
                "username": username,
                "enabled": True,
                "credentials": [
                    {
                        "value": password,
                        "type": "password",
                    }
                ],
            }
        )
        return new_user_id

    def assign_client_roles(
        self, user_id: str, client_name: str, role_names: List[str]
    ):
        client_id = self.keycloak_admin.get_client_id("realm-management")
        if not client_id:
            raise Exception(f"Client with name {client_name} does not exist")
        self.log.info("Client %s has id %s", client_name, client_id)

        role_ids = []
        for role_name in role_names:
            role_rep = self.keycloak_admin.get_client_role(client_id, role_name)
            if not role_rep:
                raise Exception(f"Role with name {role_name} does not exist")
            self.log.info("Found role %s with id %s", role_rep["name"], role_rep["id"])
            role_ids.append(role_rep)

        self.log.info("Assigning roles to user %s", user_id)
        result = self.keycloak_admin.assign_client_role(
            client_id=client_id, user_id=user_id, roles=role_ids
        )
        if not result:
            log.info("Faild assigning roles %s to user %s", role_ids, user_id)


log = logging.getLogger(__name__)


def main():
    keycloak_url = os.getenv("KEYCLOAK_URL")
    kaapana_admin_user = os.getenv("KEYCLOAK_ADMIN_USERNAME")
    kaapana_admin_password = os.getenv("KEYCLOAK_ADMIN_PASSWORD")
    backend_user = os.getenv("KEYCLOAK_BACKEND_USERNAME")
    backend_password = os.getenv("KEYCLOAK_BACKEND_PASSWORD")
    # query-groups;query-users;view-users
    backend_roles_str = os.getenv("KEYCLOAK_BACKEND_ROLES")

    utils = KeycloakHelper(
        server_url=keycloak_url,
        kaapana_admin_user=kaapana_admin_user,
        kaapana_admin_passsword=kaapana_admin_password,
    )

    backend_user_id = utils.user_id(backend_user)
    if backend_user_id:
        log.info(
            f"Backend user already inplace id: {backend_user_id}, skipping user creation..."
        )
    else:
        backend_user_id = utils.create_user(backend_user, backend_password)

    client_name = "realm-management"
    roles = backend_roles_str.split(";")
    utils.assign_client_roles(backend_user_id, client_name, roles)
    log.info("Complete")


if __name__ == "__main__":
    main()
