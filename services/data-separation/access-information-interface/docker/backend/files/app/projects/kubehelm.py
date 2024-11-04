import os
import re

import requests

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
        "release_name": project.kubernetes_namespace,
        "version": kaapana_build_version,
        "extension_params": {
            "project": project.name,
            "project_namespace": project.kubernetes_namespace,
            "namespace": project.kubernetes_namespace,
        },
    }
    response = requests.post(f"{kube_helm_api}/helm-install-chart", json=payload)
    response.raise_for_status()


def is_valid_kubernetes_namespace(name: str) -> bool:
    # Check length
    if not (1 <= len(name) <= 253):
        return False
    # Check for allowed characters and valid start/end
    return bool(re.fullmatch(r"[a-z0-9]([a-z0-9.\-]*[a-z0-9])?", name))


def test_is_valid_kubernetes_namespace() -> bool:
    # Test the function

    success = True
    test_namespaces = [
        ("valid-namespace", True),  # Valid
        ("InvalidNamespace", False),  # Invalid (uppercase letters)
        ("-invalid-start", False),  # Invalid (starts with hyphen)
        ("invalid-end-", False),  # Invalid (ends with hyphen)
        ("validnamespace123", True),  # Valid
        ("valid-namespace-name", True),  # Valid
        ("valid-namespace.v1", True),  # Valid
        ("a" * 254, False),  # Invalid (too long)
    ]

    for name_tuple in test_namespaces:
        valid_response = is_valid_kubernetes_namespace(name_tuple[0])
        assert name_tuple[1] == valid_response
        success = name_tuple[1] == valid_response

    return success
