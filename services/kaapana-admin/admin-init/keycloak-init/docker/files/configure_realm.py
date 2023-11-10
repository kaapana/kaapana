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
    file = "realm_objects/group-all_data.json"
    with open(file, "r") as f:
        payload = json.load(f)
        keycloak.post_group(payload)

    ### Add role mappings to group
    roles = ["admin", "user"]
    keycloak.post_role_mapping(roles, "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    with open(file, "r") as f:
        payload = json.load(f)
        payload["credentials"] = [{"type": "password", "value": KAAPANA_INIT_PASSWORD}]
        keycloak.post_user(payload)

    ### Add client
    file = "realm_objects/kaapana-client.json"
    with open(file, "r") as f:
        payload = json.load(f)
        payload["secret"] = oidc_client_secret
        redirect_uris = []
        redirect_uris.append(f"/oauth2/callback")
        redirect_uris.append(f"/minio-console/oauth_callback/")
        keycloak.post_client(payload, redirectUris=redirect_uris)
