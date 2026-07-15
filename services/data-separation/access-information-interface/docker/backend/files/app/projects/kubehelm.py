import os
import re

import requests

from .schemas import Project

kube_helm_api = "http://kube-helm-service.admin.svc:5000/kube-helm-api"


def install_project_helm_chart(project: Project):
    """
    Install the project-namespace helm chart for the given project.

    This helm chart creates:
    * a new namespace for the project (project-<short_id>)
    * a secret with the credentials for the project-system-user
    * a job that creates the project-system-user in Keycloak and assigns a project-role to this user in the access-information-point
    """
    kaapana_build_version = os.getenv("KAAPANA_BUILD_VERSION")
    payload = {
        "name": "project-namespace",
        "release_name": project.kubernetes_namespace,
        "version": kaapana_build_version,
        "extension_params": {
            "project": project.short_id,
            "project_namespace": project.kubernetes_namespace,
            "namespace": project.kubernetes_namespace,
            "project_id": str(project.id),
        },
    }
    response = requests.post(f"{kube_helm_api}/helm-install-chart", json=payload)
    response.raise_for_status()


def update_project_namespace_label(project: Project):
    # TODO: to be implemented when kube-helm API supports updating labels of namespaces
    """
    Update the human-readable `kaapana.ai/project-name` label on the
    project's Kubernetes namespace after a rename.
    """
    pass


def is_valid_kubernetes_namespace(name: str) -> bool:
    """
    Kubernetes namespace naming convention
    * names must be at least 1 and at most 253 characters
    * names must consist only of lower case alphanumerical characters, hyphens (-) and dots (.)
    * names must not start or end with a hyphen (-)
    """
    # Check length
    if not (1 <= len(name) <= 253):
        return False
    # Check for allowed characters and valid start/end
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9.\-]*[a-z0-9])?", name))


def uninstall_project_helm_chart(project: Project):
    """
    Uninstall the project-namespace helm chart for the given project,
    removing the namespace, secrets, and associated Keycloak job.
    """
    payload = {
        "release_name": project.kubernetes_namespace,  # project-<short_id>
        "helm_command_addons": "",
        "helm_namespace": "admin",
    }
    response = requests.post(f"{kube_helm_api}/helm-delete-chart", json=payload)
    response.raise_for_status()
