import requests

from kaapanapy.settings import OpensearchSettings
from opensearchpy import OpenSearch


def get_opensearch_client(access_token=None):
    settings = OpensearchSettings()
    access_token = access_token or get_project_user_access_token()
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    return OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
            }
        ],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
    )


def get_project_user_access_token():
    """
    Return an access token of the project user.
    """
    from kaapanapy.settings import ProjectSettings, KeycloakSettings

    project_settings = ProjectSettings()
    keycloak_settings = KeycloakSettings()
    payload = {
        "username": project_settings.project_user_name,
        "password": project_settings.project_user_password,
        "client_id": keycloak_settings.client_id,
        "client_secret": keycloak_settings.client_secret,
        "grant_type": "password",
    }
    url = f"{keycloak_settings.keycloak_url}/auth/realms/{keycloak_settings.client_id}/protocol/openid-connect/token"
    r = requests.post(url, verify=False, data=payload)
    access_token = r.json()["access_token"]
    return access_token
