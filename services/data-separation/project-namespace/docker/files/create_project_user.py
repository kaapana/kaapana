from KeycloakHelper import KeycloakHelper
import requests
import os


if __name__ == "__main__":
    kc_client = KeycloakHelper()
    project_user = os.getenv("PROJECT_USER")
    project_user_password = os.getenv("PROJECT_USER_PASSWORD")
    user_payload = {
        "username": project_user,
        "credentials": [{"type": "password", "value": project_user_password}],
        "enabled": True,
        "emailVerified": False,
        "firstName": project_user,
        "lastName": "System",
        "email": "",
        "requiredActions": [],
        "groups": ["kaapana_user"],
    }
    kc_client.post_user(user_payload, reset_password=True)

    keycloak_user = kc_client.get_user_by_name(project_user)
    keycloak_user_id = keycloak_user.get("id")

    ### Add role mappings to system user in access-information-point
    project_name = os.getenv("PROJECT_NAME")
    SERVICE_NAMESPACE = os.getenv("SERVICES_NAMESPACE")
    project_user_role = "admin"
    response = requests.post(
        f"http://aii-service.{SERVICE_NAMESPACE}.svc:8080/projects/{project_name}/role/{project_user_role}/user/{keycloak_user_id}"
    )
    response.raise_for_status()
