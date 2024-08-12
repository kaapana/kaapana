import requests
import os
from .schemas import Project

kube_helm_api = "http://kube-helm-service.admin.svc:5000/kube-helm-api"


def install_kubernetes_project(project: Project):
    kaapana_build_version = os.getenv("KAAPANA_BUILD_VERSION")
    payload = {
        "name": "project-namespace",
        "version": kaapana_build_version,
        "keywords": ["kaapanaapplication", "kaapanamultiinstallable"],
        "extension_params": {"project_namespace": project.name},
    }
    response = requests.post(f"{kube_helm_api}/helm-install-chart", json=payload)
    response.raise_for_status()
