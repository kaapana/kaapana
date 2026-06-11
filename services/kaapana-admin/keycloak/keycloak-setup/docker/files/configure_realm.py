from KeycloakHelper import KeycloakHelper
import os, json
from logger import get_logger
from pathlib import Path
import logging

REALM_OBJECTS_ROOT_DIR = Path(os.getenv("REALM_OBJECTS_ROOT_DIR", "/realm_objects"))
DEV_MODE = os.getenv("DEV_MODE")
log_level = logging.DEBUG if DEV_MODE.lower() == "true" else logging.INFO
logger = get_logger(__name__, log_level)

if __name__ == "__main__":
    logger.info("Starting configure_realm ...")
    keycloak = KeycloakHelper()
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
    service_account_user = "service-account-kaapana-service"
    for role in ["manage-users", "query-users", "query-groups", "view-realm"]:
        keycloak.post_client_role_mapping(
            "realm-management", role, service_account_user
        )
