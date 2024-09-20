import requests
import json
import os
from kaapanapy.logger import get_logger
from kaapanapy.helper import get_project_user_access_token

logger = get_logger(__name__)
SERVICES_NAMESPACE = os.getenv("SERVICES_NAMESPACE")

file_path = "/app/config/initial_projects.json"
aii_service = f"http://aii-service.{SERVICES_NAMESPACE}.svc:8080"

if __name__ == "__main__":
    access_token = get_project_user_access_token()
    auth_header = {"x-forwarded-access-token": access_token}
    response = requests.get(f"{aii_service}/projects", headers=auth_header)
    existing_projects = response.json()

    ### Request creation of projects existing in the access-information-point
    ### This will recreate the project-specific kubernetes namespaces, in case they got deleted during a undeployment
    for project in existing_projects:
        logger.info(f"Request creation of {project=}")
        create_project = {}
        create_project["name"] = project.get("name")
        create_project["description"] = project.get("description")
        create_project["external_id"] = project.get("external_id")

        response = requests.post(
            f"{aii_service}/projects",
            data=json.dumps(create_project),
            headers=auth_header,
        )
        response.raise_for_status()

    with open(file_path, "r") as file:
        initial_project = json.load(file)
    existing_project_names = [project.get("name") for project in existing_projects]

    ### Create all initial projects that do not already exist in the access-information-point
    for project in initial_project:
        if project.get("name") in existing_project_names:
            continue
        logger.info(f"Request creation of {project=}")
        response = requests.post(
            f"{aii_service}/projects", data=json.dumps(project), headers=auth_header
        )
        response.raise_for_status()
