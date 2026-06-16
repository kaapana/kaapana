from KeycloakHelper import KeycloakHelper
import os, json, sys
import requests
from logger import get_logger
from pathlib import Path
import logging

REALM_OBJECTS_ROOT_DIR = Path(os.getenv("REALM_OBJECTS_ROOT_DIR", "/realm_objects"))
DEV_MODE = os.getenv("DEV_MODE")
log_level = logging.DEBUG if DEV_MODE.lower() == "true" else logging.INFO
logger = get_logger(__name__, log_level)


def _service_client_functional(host: str, port: int, secret: str) -> bool:
    try:
        r = requests.post(
            f"https://{host}:{port}/auth/realms/kaapana/protocol/openid-connect/token",
            verify=False,
            data={
                "client_id": "kaapana-service",
                "client_secret": secret,
                "grant_type": "client_credentials",
            },
            timeout=10,
        )
        return r.status_code == 200
    except Exception:
        return False


def _get_service_token(host: str, port: int, secret: str) -> str:
    r = requests.post(
        f"https://{host}:{port}/auth/realms/kaapana/protocol/openid-connect/token",
        verify=False,
        data={
            "client_id": "kaapana-service",
            "client_secret": secret,
            "grant_type": "client_credentials",
        },
        timeout=10,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def _update_oidc_client_secret(
    host: str, port: int, service_token: str, new_secret: str
) -> None:
    """Update the kaapana OIDC client secret using kaapana-service token (requires manage-clients role)."""
    admin_url = f"https://{host}:{port}/auth/admin/realms/kaapana/"
    headers = {"Authorization": f"Bearer {service_token}"}
    r = requests.get(
        f"{admin_url}clients?clientId=kaapana",
        verify=False,
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    clients = r.json()
    if not clients:
        raise ValueError("kaapana OIDC client not found in Keycloak")
    client_uuid = clients[0]["id"]
    client_rep = clients[0]
    client_rep["secret"] = new_secret
    r = requests.put(
        f"{admin_url}clients/{client_uuid}",
        verify=False,
        json=client_rep,
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()


def _reset_system_user_password(
    host: str, port: int, service_token: str, new_password: str
) -> None:
    """Sync the system user's password using kaapana-service token (requires manage-users role)."""
    admin_url = f"https://{host}:{port}/auth/admin/realms/kaapana/"
    headers = {"Authorization": f"Bearer {service_token}"}
    r = requests.get(
        f"{admin_url}users?username=system&exact=true",
        verify=False,
        headers=headers,
        timeout=10,
    )
    r.raise_for_status()
    users = r.json()
    if not users:
        raise ValueError("system user not found in Keycloak")
    user_id = users[0]["id"]
    r = requests.put(
        f"{admin_url}users/{user_id}/reset-password",
        verify=False,
        json={"type": "password", "value": new_password, "temporary": False},
        headers=headers,
        timeout=10,
    )
    if r.status_code == 400:
        # Password policy rejection (e.g., same password already set) — password already matches
        logger.warning(
            "System user password reset rejected by policy — already set to target value."
        )
        return
    r.raise_for_status()


if __name__ == "__main__":
    logger.info("Starting configure_realm ...")

    keycloak_host = os.environ.get("KEYCLOAK_HOST", "")
    keycloak_port = int(os.getenv("KEYCLOAK_HTTPS_PORT", 443))
    service_secret = os.environ.get("KEYCLOAK_SERVICE_CLIENT_SECRET", "")

    try:
        keycloak = KeycloakHelper()
    except Exception as e:
        logger.warning(f"Admin authentication failed: {e}")
        if _service_client_functional(keycloak_host, keycloak_port, service_secret):
            logger.info(
                "kaapana-service client is functional — realm already configured. Syncing secrets..."
            )
            oidc_client_secret = os.environ["OIDC_CLIENT_SECRET"]
            system_user_password = os.environ["SYSTEM_USER_PASSWORD"]
            service_token = _get_service_token(
                keycloak_host, keycloak_port, service_secret
            )
            _update_oidc_client_secret(
                keycloak_host, keycloak_port, service_token, oidc_client_secret
            )
            logger.info("OIDC client secret updated.")
            _reset_system_user_password(
                keycloak_host, keycloak_port, service_token, system_user_password
            )
            logger.info("System user password synced. Skipping full realm setup.")
            sys.exit(0)
        logger.error(
            "Admin authentication failed and kaapana-service client is not available. "
            "Cannot configure realm. Provide the current Keycloak admin password."
        )
        sys.exit(1)

    oidc_client_secret = os.environ["OIDC_CLIENT_SECRET"]
    KAAPANA_INIT_PASSWORD = os.getenv("KAAPANA_INIT_PASSWORD")
    logger.info(f"{DEV_MODE=}")
    logger.info(f"{KAAPANA_INIT_PASSWORD=}")

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
        payload["credentials"] = [{"type": "password", "value": KAAPANA_INIT_PASSWORD}]
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
    for role in [
        "manage-users",
        "query-users",
        "query-groups",
        "view-realm",
        "manage-clients",
    ]:
        keycloak.post_service_account_role_mapping(
            "kaapana-service", "realm-management", role
        )
