from KeycloakHelper import KeycloakHelper
import os, json
from logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)

if __name__ == "__main__":
    logger.info("Starting configure_realm ...")
    keycloak = KeycloakHelper()
    oidc_client_secret = os.environ["OIDC_CLIENT_SECRET"]
    DEV_MODE = os.getenv("DEV_MODE")
    KAAPANA_INIT_PASSWORD = os.getenv("KAAPANA_INIT_PASSWORD")
    logger.info(f"{DEV_MODE=}")
    logger.info(f"{KAAPANA_INIT_PASSWORD=}")
    ### Add realm
    file = "realm_objects/kaapana-realm.json"
    payload = json.load(open(file, "r"))
    if DEV_MODE.lower() == "true":
        payload["passwordPolicy"] = ""
        logger.warning("!! DEV_MODE: Set password policies to emtpy string.")
    logger.debug(f"{payload=}")
    keycloak.post_realm(payload)

    ### Add group
    file = "realm_objects/group-all_data.json"
    payload = json.load(open(file, "r"))
    keycloak.post_group(payload)

    ### Add role mappings to group
    roles = ["admin", "user"]
    keycloak.post_role_mapping(roles, "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    payload = json.load(open(file, "r"))
    payload["credentials"] = [{"type": "password", "value": KAAPANA_INIT_PASSWORD}]
    keycloak.post_user(payload)

    ### Add client
    file = "realm_objects/kaapana-client.json"
    payload = json.load(open(file, "r"))
    payload["secret"] = oidc_client_secret
    KEYCLOAK_URI = os.environ["KEYCLOAK_URI"]

    redirect_uris = []
    redirect_uris.append(f"/oauth2/callback")
    redirect_uris.append(f"{KEYCLOAK_URI}/minio-console/oauth_callback/")
    keycloak.post_client(payload, redirectUris=redirect_uris)
