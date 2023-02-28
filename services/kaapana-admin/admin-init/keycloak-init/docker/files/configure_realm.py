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

    ### Add group
    file = "realm_objects/group-all_data.json"
    payload = json.load(open(file,"r"))
    keycloak.post_group(payload)

    ### Add role mappings to group
    roles = ["admin", "user"]
    keycloak.post_role_mapping(roles, "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    payload = json.load(open(file,"r"))
    keycloak.post_user(payload)

    ### Add client 
    file = "realm_objects/kaapana-client.json"
    payload = json.load(open(file,"r"))
    KEYCLOAK_URI = os.environ["KEYCLOAK_URI"]
    
    redirect_uris = []
    redirect_uris.append(f"/oauth2/callback")
    redirect_uris.append(f"{KEYCLOAK_URI}/minio-console/oauth_callback/")
    keycloak.post_client(payload, redirectUris=redirect_uris)


