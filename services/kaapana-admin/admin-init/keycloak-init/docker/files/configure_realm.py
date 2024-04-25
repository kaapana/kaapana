from KeycloakHelper import KeycloakHelper
import os, json
from logger import get_logger
import logging


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
    file = "realm_objects/kaapana-realm.json"
    with open(file, "r") as f:
        payload = json.load(f)
        if DEV_MODE.lower() == "true":
            payload["passwordPolicy"] = ""
            logger.warning("!! DEV_MODE: Set password policies to emtpy string.")
        logger.debug(f"{payload=}")
        keycloak.post_realm(payload)

    ### Add user role to default-roles-kaapana
    keycloak.post_composite_role("default-roles-kaapana", ["user"])

    ### Add group
    file = "realm_objects/group-kaapana_admin.json"
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group kaapana_admin
    roles = ["admin", "user"]
    keycloak.post_role_mapping(roles, "kaapana_admin")

    ### Add kaapana_user group kaapana_user
    file = "realm_objects/group-kaapana_user.json"
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group kaapana_user
    roles = ["user"]
    keycloak.post_role_mapping(roles, "kaapana_user")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    with open(file, "r") as f:
        payload = json.load(f)
        payload["credentials"] = [{"type": "password", "value": KAAPANA_INIT_PASSWORD}]
        keycloak.post_user(payload)

    ### Add system user
    file = "realm_objects/system-user.json"
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
    file = "realm_objects/kaapana-client.json"
    with open(file, "r") as f:
        payload = json.load(f)
        payload["secret"] = oidc_client_secret
        redirect_uris = []
        redirect_uris.append(f"/oauth2/callback")
        hostname = os.getenv("HOSTNAME")
        https_port = os.getenv("HTTPS_PORT")
        redirect_uris.append(
            f"https://{hostname}:{https_port}/minio-console/oauth_callback/"
        )
        redirect_uris.append(f"https://{hostname}/meta/auth/openid/login")
        keycloak.post_client(payload, redirectUris=redirect_uris)
