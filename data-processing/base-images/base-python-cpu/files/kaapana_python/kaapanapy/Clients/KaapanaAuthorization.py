import requests


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
