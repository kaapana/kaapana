"""
Bootstrap of the kaapana-admin Keycloak client (master realm).

This is the only step that may need the Keycloak admin password, and only on the
very first bootstrap: it follows an admin-client-first strategy. If the
kaapana-admin client already authenticates via client_credentials, the bootstrap
is a no-op and no admin password is required (redeploys, also after an admin
password change).

The kaapana-admin client is a master-realm service-account client with the master
'admin' realm role — i.e. full admin rights across realms. The setup job
(configure_realm.py) authenticates as this client, so the admin password never
reaches the setup job nor any runtime pod.
"""

import logging
import os
import sys

import requests
from KeycloakHelper import KeycloakHelper
from logger import get_logger

logger = get_logger(__name__, logging.INFO)

ADMIN_CLIENT_ID = "kaapana-admin"

ADMIN_CLIENT_REPRESENTATION = {
    "clientId": ADMIN_CLIENT_ID,
    "enabled": True,
    "protocol": "openid-connect",
    "clientAuthenticatorType": "client-secret",
    "serviceAccountsEnabled": True,
    "publicClient": False,
    "standardFlowEnabled": False,
    "implicitFlowEnabled": False,
    "directAccessGrantsEnabled": False,
    "bearerOnly": False,
}


def _admin_client_functional(host: str, port: int, secret: str) -> bool:
    """Return True if the kaapana-admin client can already authenticate."""
    try:
        r = requests.post(
            f"https://{host}:{port}/auth/realms/master/protocol/openid-connect/token",
            verify=False,
            data={
                "client_id": ADMIN_CLIENT_ID,
                "client_secret": secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_master_client_uuid(keycloak: KeycloakHelper) -> str:
    clients = keycloak.make_authorized_request(
        keycloak.auth_url + "master/clients", requests.get
    ).json()
    for client in clients:
        if client["clientId"] == ADMIN_CLIENT_ID:
            return client["id"]
    return None


def _set_admin_password_temporary(keycloak: KeycloakHelper) -> None:
    """Add UPDATE_PASSWORD required action to the master-realm admin user.

    This forces a password change on the next Keycloak UI login without affecting
    client_credentials flows — service accounts authenticate independently of
    the admin user's login state.
    """
    base = keycloak.auth_url
    users = keycloak.make_authorized_request(
        base + "master/users?username=admin&exact=true", requests.get
    ).json()
    if not users:
        logger.warning("Master-realm admin user not found — skipping temporary flag.")
        return
    user = users[0]
    if "UPDATE_PASSWORD" not in user.get("requiredActions", []):
        user["requiredActions"] = user.get("requiredActions", []) + ["UPDATE_PASSWORD"]
        keycloak.make_authorized_request(
            base + f"master/users/{user['id']}", requests.put, user
        )
        logger.info(
            "Admin password marked as temporary — must be changed on next UI login."
        )


def _create_admin_client(keycloak: KeycloakHelper, client_secret: str) -> None:
    """Create/update the kaapana-admin client and grant it the master 'admin' role."""
    payload = dict(ADMIN_CLIENT_REPRESENTATION, secret=client_secret)
    base = keycloak.auth_url  # https://host:port/auth/admin/realms/

    client_uuid = _get_master_client_uuid(keycloak)
    if client_uuid:
        logger.info("kaapana-admin client exists — updating secret.")
        keycloak.make_authorized_request(
            base + f"master/clients/{client_uuid}", requests.put, payload
        )
    else:
        logger.info("Creating kaapana-admin client in master realm.")
        keycloak.make_authorized_request(
            base + "master/clients", requests.post, payload
        )
        client_uuid = _get_master_client_uuid(keycloak)

    # Grant the master realm 'admin' role to the service account (full admin rights).
    service_account_user_id = keycloak.make_authorized_request(
        base + f"master/clients/{client_uuid}/service-account-user", requests.get
    ).json()["id"]
    admin_role = keycloak.make_authorized_request(
        base + "master/roles/admin", requests.get
    ).json()
    keycloak.make_authorized_request(
        base + f"master/users/{service_account_user_id}/role-mappings/realm",
        requests.post,
        [admin_role],
    )


if __name__ == "__main__":
    logger.info("Starting kaapana-admin bootstrap ...")

    keycloak_host = os.environ["KEYCLOAK_HOST"]
    keycloak_port = int(os.getenv("KEYCLOAK_HTTPS_PORT", 443))
    admin_client_secret = os.environ["KAAPANA_ADMIN_CLIENT_SECRET"]

    if _admin_client_functional(keycloak_host, keycloak_port, admin_client_secret):
        logger.info(
            "kaapana-admin client already functional — skipping bootstrap "
            "(no admin password required)."
        )
        sys.exit(0)

    logger.info(
        "kaapana-admin client not available — bootstrapping with admin password."
    )
    try:
        keycloak = KeycloakHelper.from_admin_password()
    except Exception as e:
        logger.error(
            f"Admin authentication failed and kaapana-admin client is missing: {e}. "
            "Provide the current Keycloak admin password to bootstrap."
        )
        sys.exit(1)

    _create_admin_client(keycloak, admin_client_secret)
    logger.info("kaapana-admin client bootstrapped and granted master admin role.")

    if os.getenv("KAAPANA_ADMIN_PASSWORD_TEMPORARY", "false").lower() == "true":
        _set_admin_password_temporary(keycloak)
