from KeycloakHelper import KeycloakHelper
import os, json

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
    keycloak.post_role_mapping(["admin", "user"], "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    payload = json.load(open(file,"r"))
    keycloak.post_user(payload)

    ### Add client 
    file = "realm_objects/kaapana-client.json"
    host = os.environ["HOSTNAME"]
    payload = json.load(open(file,"r"))
    keycloak.post_client(payload, redirectUris=[ "/oauth2/callback", f"https://{host}:443/minio-console/oauth_callback/" ])


