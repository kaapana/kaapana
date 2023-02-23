from KeycloakHelper import KeycloakHelper
import os

if __name__=='__main__':
    keycloak = KeycloakHelper()
    
    ### Add realm
    file = "realm_objects/kaapana-realm.json"
    keycloak.post_realm(file)

    ### Add group
    file = "realm_objects/group-all_data.json"
    keycloak.post_group(file)
    keycloak.get_groups()

    ### Add role mappings to group
    file = "realm_objects/role-mappings.json"
    keycloak.post_role_mapping(["admin", "user"], "all_data")

    ### Add user
    file = "realm_objects/kaapana-user.json"
    keycloak.post_user(file)

    ### Add client 
    file = "realm_objects/kaapana-client.json"
    host = os.environ["HOSTNAME"]
    keycloak.post_client(file, redirectUris=[ "/oauth2/callback", f"https://{host}:443/minio-console/oauth_callback/" ])


