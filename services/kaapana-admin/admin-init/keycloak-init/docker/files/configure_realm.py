from KeycloakHelper import KeycloakHelper
import os, json
from logger import get_logger
import logging

logger = get_logger(__name__, logging.DEBUG)


if __name__=='__main__':
    keycloak = KeycloakHelper()
    
    ### Add realm
    file = "realm_objects/kaapana-realm.json"
    payload = json.load(open(file,"r"))
    keycloak.post_realm(payload)
    logger.info("Kaapana realm created.")

    ### Add group
    file = "realm_objects/group-all_data.json"
    payload = json.load(open(file,"r"))
    keycloak.post_group(payload)
    logger.info("Creating group all_data in realm kaapana.")

    ### Add role mappings to group
    roles = ["admin", "user"]
    keycloak.post_role_mapping(roles, "all_data")
    logger.info(f"Add {roles} to group all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    payload = json.load(open(file,"r"))
    keycloak.post_user(payload)
    logger.info("Create kaapana user in realm kaapana and group all_data")

    ### Add client 
    file = "realm_objects/kaapana-client.json"
    payload = json.load(open(file,"r"))
    host = os.environ["HOSTNAME"]
    https_port = os.environ["HTTPS_PORT"]
    
    redirect_uris = [f"https://{host}:{https_port}/oauth2/callback"]
    redirect_uris.append(f"https://{host}:{https_port}/minio-console/oauth_callback/")
    keycloak.post_client(payload, redirectUris=redirect_uris)
    logger.info("Create kaapana client in realm kaapana.")



