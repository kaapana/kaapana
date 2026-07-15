"""
Bootstrap of the kaapana-admin Keycloak client (master realm) and (re)setting of
the master-realm admin password.

Every deploy hands this job a desired admin password (``KEYCLOAK_PASSWORD``) and
the kaapana-admin client secret (``KAAPANA_ADMIN_CLIENT_SECRET``).

What it expects (env):
  ``KEYCLOAK_HOST`` / ``KEYCLOAK_HTTPS_PORT`` - the Keycloak address.
  ``KAAPANA_ADMIN_CLIENT_SECRET``            - the kaapana-admin client secret.
  ``KEYCLOAK_USER`` / ``KEYCLOAK_PASSWORD``  - the master admin user and the
                                               password to apply to it.
  ``KAAPANA_ADMIN_PASSWORD_TEMPORARY``       - "true" marks the password as
                                               temporary (must be changed on the
                                               next login; used for generated
                                               passwords).

What it guarantees after a successful run:
  * the kaapana-admin client exists in the master realm with the given secret and
    the master 'admin' realm role (full admin rights), so the setup job and all
    later deploys authenticate via the client and never need the admin password;
  * the master-realm admin user's password equals ``KEYCLOAK_PASSWORD``.

Behaviour:
  * Client secret already works -> authenticate via the client (no admin password
    required) and reset the admin password to ``KEYCLOAK_PASSWORD``. If no
    password was supplied, only warn - the connection works, but running without
    a password is not the intended path.
  * Client secret missing or stale -> authenticate with the admin password to
    create/repair the client, then apply the admin password. Without an admin
    password this is impossible and the job fails with a clear error.

The admin password never reaches the setup job nor any runtime pod.
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


def _set_admin_password(
    keycloak: KeycloakHelper, username: str, password: str, temporary: bool
) -> None:
    """Set the master-realm admin user's password.

    With ``temporary`` it must be changed on the next login; a temporary
    credential is what Keycloak 26 reliably enforces at the admin-console login
    (the UPDATE_PASSWORD required action is not honoured for this user).
    client_credentials flows are unaffected - service accounts authenticate
    independently of the admin user's login state.
    """
    base = keycloak.auth_url
    users = keycloak.make_authorized_request(
        base + f"master/users?username={username}&exact=true", requests.get
    ).json()
    if not users:
        logger.warning("Master-realm admin user not found - skipping password set.")
        return
    user_id = users[0]["id"]
    keycloak.make_authorized_request(
        base + f"master/users/{user_id}/reset-password",
        requests.put,
        {"type": "password", "value": password, "temporary": temporary},
    )
    logger.info(
        "Master-realm admin password set (%s).",
        "temporary" if temporary else "permanent",
    )


def _create_admin_client(keycloak: KeycloakHelper, client_secret: str) -> None:
    """Create/update the kaapana-admin client and grant it the master 'admin' role."""
    payload = dict(ADMIN_CLIENT_REPRESENTATION, secret=client_secret)
    base = keycloak.auth_url  # https://host:port/auth/admin/realms/

    client_uuid = _get_master_client_uuid(keycloak)
    if client_uuid:
        logger.info("kaapana-admin client exists - updating secret.")
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
    admin_user = os.environ["KEYCLOAK_USER"]
    admin_password = os.getenv("KEYCLOAK_PASSWORD", "")
    temporary = os.getenv("KAAPANA_ADMIN_PASSWORD_TEMPORARY", "false").lower() == "true"

    if _admin_client_functional(keycloak_host, keycloak_port, admin_client_secret):
        logger.info(
            "kaapana-admin client already functional - no admin password needed "
            "to authenticate."
        )
        if not admin_password:
            logger.warning(
                "No admin password supplied, but the kaapana-admin client works. "
                "The connection is fine, but the admin password was NOT (re)set - "
                "this job is not meant to run without a password."
            )
            sys.exit(0)
        keycloak = KeycloakHelper.from_client_credentials(
            ADMIN_CLIENT_ID,
            admin_client_secret,
            realm="master",
            keycloak_host=keycloak_host,
            keycloak_https_port=keycloak_port,
        )
        _set_admin_password(keycloak, admin_user, admin_password, temporary)
        logger.info("Admin password (re)set via the kaapana-admin client.")
        sys.exit(0)

    # Client secret missing or stale - the admin password is required to create it.
    if not admin_password:
        logger.error(
            "kaapana-admin client is not functional and no admin password was "
            "supplied - cannot bootstrap. Provide the current Keycloak admin "
            "password (on a migration this is your existing one)."
        )
        sys.exit(1)

    logger.info(
        "kaapana-admin client not available - bootstrapping with the admin password."
    )
    try:
        keycloak = KeycloakHelper.from_admin_password()
    except Exception as e:
        logger.error(
            f"Admin authentication failed and the kaapana-admin client is missing: "
            f"{e}. Check that the supplied password matches the current Keycloak "
            "admin password."
        )
        sys.exit(1)

    try:
        _create_admin_client(keycloak, admin_client_secret)
    except Exception as e:
        logger.error(
            f"Could not create the kaapana-admin client: {e}. Check the Keycloak "
            "server logs and the admin user's permissions."
        )
        sys.exit(1)

    try:
        _set_admin_password(keycloak, admin_user, admin_password, temporary)
    except Exception as e:
        logger.error(
            f"kaapana-admin client created, but applying the admin password "
            f"failed: {e}."
        )
        sys.exit(1)

    logger.info("kaapana-admin client bootstrapped and admin password set.")
