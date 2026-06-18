from KeycloakHelper import KeycloakHelper
import os, json, time
from logger import get_logger
from pathlib import Path
import logging
import requests

REALM_OBJECTS_ROOT_DIR = Path(os.getenv("REALM_OBJECTS_ROOT_DIR", "/realm_objects"))
DEV_MODE = os.getenv("DEV_MODE")
log_level = logging.DEBUG if DEV_MODE.lower() == "true" else logging.INFO
logger = get_logger(__name__, log_level)

# Minimal realm-management roles for the runtime kaapana-service client.
# Deliberately WITHOUT manage-clients — the setup job authenticates as the
# kaapana-admin client, so kaapana-service never needs to manage clients.
_SERVICE_ACCOUNT_ROLES = [
    "manage-users",
    "query-users",
    "query-groups",
    "view-realm",
]

_MAX_RETRIES = 5
_RETRY_BASE_DELAY = 5  # seconds; doubles on each retry: 5, 10, 20, 40, 80


def _run_setup(keycloak, oidc_client_secret, kaapana_init_password):
    """Full realm configuration — all operations are idempotent (409 handled)."""

    ### Add realm
    file = Path(REALM_OBJECTS_ROOT_DIR, "kaapana-realm.json")
    with open(file, "r") as f:
        payload = json.load(f)
        if DEV_MODE.lower() == "true":
            payload["passwordPolicy"] = ""
            logger.warning("!! DEV_MODE: Set password policies to empty string.")
        logger.debug(f"{payload=}")
        keycloak.post_realm(payload)

    ### Add user role to default-roles-kaapana
    keycloak.post_composite_role("default-roles-kaapana", ["user"])

    ### Add group kaapana_admin
    file = Path(REALM_OBJECTS_ROOT_DIR, "group-kaapana_admin.json")
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group kaapana_admin
    roles = ["admin", "project-manager", "user"]
    keycloak.post_role_mapping(roles_to_add=roles, group="kaapana_admin")

    ### Add group kaapana_user
    file = Path(REALM_OBJECTS_ROOT_DIR, "group-kaapana_user.json")
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group kaapana_user
    roles = ["user"]
    keycloak.post_role_mapping(roles_to_add=roles, group="kaapana_user")

    ### Add group kaapana_project_manager
    file = Path(REALM_OBJECTS_ROOT_DIR, "group-kaapana_project_manager.json")
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group kaapana_project_manager
    roles = ["project-manager", "user"]
    keycloak.post_role_mapping(roles_to_add=roles, group="kaapana_project_manager")

    ### Add user
    file = Path(REALM_OBJECTS_ROOT_DIR, "kaapana-user.json")
    with open(file, "r") as f:
        payload = json.load(f)
        payload["credentials"] = [{"type": "password", "value": kaapana_init_password}]
        keycloak.post_user(payload)

    ### Add system user
    file = Path(REALM_OBJECTS_ROOT_DIR, "system-user.json")
    with open(file, "r") as f:
        system_user_password = os.getenv("SYSTEM_USER_PASSWORD")
        assert system_user_password
        payload = json.load(f)
        payload["credentials"] = [{"type": "password", "value": system_user_password}]
        keycloak.post_user(payload, reset_password=True)

    ### Add impersonation role to system user
    keycloak.post_client_role_mapping("realm-management", "impersonation", "system")
    ### Add dcm4chee-admin-role to system user
    keycloak.post_role_mapping(["dcm4chee-admin"], user="system")

    ### Add client
    file = Path(REALM_OBJECTS_ROOT_DIR, "kaapana-client.json")
    with open(file, "r") as f:
        payload = json.load(f)
        payload["secret"] = oidc_client_secret
        redirect_uris = []
        redirect_uris.append(f"/oauth2/callback")
        hostname = os.getenv("HOSTNAME")
        https_port = os.getenv("HTTPS_PORT")
        redirect_uris.append(f"https://{hostname}:{https_port}/oauth2/callback")
        redirect_uris.append(
            f"https://{hostname}:{https_port}/minio-console/oauth_callback/"
        )
        redirect_uris.append(f"https://{hostname}:{https_port}/meta/auth/openid/login")
        keycloak.post_client(payload, redirectUris=redirect_uris)

    ### Add services client
    file = Path(REALM_OBJECTS_ROOT_DIR, "kaapana-service.json")
    with open(file, "r") as f:
        payload = json.load(f)
        payload["secret"] = os.environ["KEYCLOAK_SERVICE_CLIENT_SECRET"]
        keycloak.post_client(payload)

    ### Assign realm-management roles to service account
    for role in _SERVICE_ACCOUNT_ROLES:
        keycloak.post_service_account_role_mapping(
            "kaapana-service", "realm-management", role
        )


if __name__ == "__main__":
    logger.info("Starting configure_realm ...")

    oidc_client_secret = os.environ["OIDC_CLIENT_SECRET"]
    kaapana_init_password = os.getenv("KAAPANA_INIT_PASSWORD")
    logger.info(f"{DEV_MODE=}")
    logger.info(f"{kaapana_init_password=}")

    for _attempt in range(1, _MAX_RETRIES + 1):
        try:
            # A fresh token is obtained on every attempt to avoid expiry after retries.
            # The admin password is never needed here — the bootstrap job created the
            # kaapana-admin client and its secret is the only persisted credential.
            keycloak = KeycloakHelper.from_client_credentials(
                "kaapana-admin",
                os.environ["KAAPANA_ADMIN_CLIENT_SECRET"],
                realm="master",
            )
            _run_setup(keycloak, oidc_client_secret, kaapana_init_password)
            break
        except requests.exceptions.HTTPError as e:
            delay = _RETRY_BASE_DELAY * (2 ** (_attempt - 1))
            if (
                e.response is not None
                and e.response.status_code == 403
                and _attempt < _MAX_RETRIES
            ):
                # Keycloak cold-start race: realm just created, admin API not yet ready.
                # All operations are idempotent — safe to retry from scratch.
                logger.warning(
                    f"403 Forbidden on attempt {_attempt}/{_MAX_RETRIES} "
                    f"(Keycloak initializing). Retrying in {delay}s ..."
                )
                time.sleep(delay)
            else:
                raise
