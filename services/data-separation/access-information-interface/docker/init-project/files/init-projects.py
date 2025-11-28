import json
import os
from typing import Dict, List
from uuid import UUID

import requests
from kaapanapy.helper import get_project_user_access_token
from kaapanapy.logger import get_logger
from KeycloakHelper import KeycloakHelper

logger = get_logger(__name__)
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")

FILE_PATH = "/app/config/initial_projects.json"
AII_SERVICE = f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080"


def get_existing_projects(auth_header: Dict[str, str]) -> List[Dict[str, str]]:
    """Fetches existing projects from the AII service."""
    response = requests.get(f"{AII_SERVICE}/projects", headers=auth_header)
    response.raise_for_status()
    return response.json()


def create_project_if_not_exists(project, auth_header):
    """Creates a project in the AII service if it doesn't already exist."""
    response = requests.post(
        f"{AII_SERVICE}/projects", data=json.dumps(project), headers=auth_header
    )
    response.raise_for_status()


def map_user_to_project_role(
    project_id: UUID, role: str, user_id: str, auth_header: Dict[str, str]
):
    """Maps the user to the specified role in the specified project."""
    response = requests.post(
        f"{AII_SERVICE}/projects/{project_id}/role/{role}/user/{user_id}",
        headers=auth_header,
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 409:
            pass  # If conflict (user already mapped), do nothing
        else:
            logger.error(
                f"Failed to create project mapping for {project_id=}, {role=}, {user_id=}"
            )
            raise e


def get_keycloak_user_id(username):
    """Fetches the Keycloak user ID for the given username."""
    kc_client = KeycloakHelper()
    keycloak_user = kc_client.get_user_by_name(username)
    return keycloak_user.get("id")


def load_initial_projects():
    """Loads the initial projects from the JSON file."""
    with open(FILE_PATH, "r") as file:
        return json.load(file)


def main():
    access_token = get_project_user_access_token()
    auth_header = {"x-forwarded-access-token": access_token}

    # Fetch existing projects
    existing_projects = get_existing_projects(auth_header)
    existing_project_names = {project["name"] for project in existing_projects}

    # Create projects that exist in AII service
    for project in existing_projects:
        logger.info(f"Request creation of {project['name']}")
        create_project_if_not_exists(project, auth_header)

    # Load initial projects
    initial_projects = load_initial_projects()

    # Create projects that do not already exist in AII service
    for project in initial_projects:
        if project["name"] not in existing_project_names:
            logger.info(f"Request creation of {project['name']}")
            create_project_if_not_exists(project, auth_header)

    # Get the Keycloak user ID for the "kaapana" user
    keycloak_user_id = get_keycloak_user_id("kaapana")

    # Map the Kaapana admin user to the "admin" project and the "admin" role
    response = requests.get(f"{AII_SERVICE}/projects/admin", headers=auth_header)
    response.raise_for_status()
    project_id = response.json()["id"]
    # Assign the user to the admin project with admin role

    map_user_to_project_role(
        project_id, "principal-investigator", keycloak_user_id, auth_header
    )

    logger.info("Initial projects created and user mapped successfully")


if __name__ == "__main__":
    main()
