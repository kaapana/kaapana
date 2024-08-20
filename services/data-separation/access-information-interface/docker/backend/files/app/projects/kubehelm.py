import requests
import os
from .schemas import Project

kube_helm_api = "http://kube-helm-service.admin.svc:5000/kube-helm-api"


def install_project_helm_chart(project: Project):
    """
    Install the project-namespace helm chart for the given project.
    This helm chart contains
    * a new namespace for the project
    * a secret with the credentials for the project-system-user
    * a job that creates the project-system-user in Keycloak and assigns a project-role to this user in the access-information-point
    """
    kaapana_build_version = os.getenv("KAAPANA_BUILD_VERSION")
    payload = {
        "name": "project-namespace",
        "release_name": f"project-{project.name}",
        "version": kaapana_build_version,
        "extension_params": {
            "project": project.name,
            "project_namespace": f"project-{project.name}",
            "namespace": f"project-{project.name}",
        },
    }
    response = requests.post(f"{kube_helm_api}/helm-install-chart", json=payload)
    response.raise_for_status()
