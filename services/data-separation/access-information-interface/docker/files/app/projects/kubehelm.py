import requests
from .schemas import Project

kube_helm_api = "http://kube-helm-service.admin.svc:5000/kube-helm-api"


def install_kubernetes_project(project: Project):
    payload = {
        "name": "project-namespace",
        "version": "0.0.0",
        "keywords": ["kaapanaapplication", "kaapanamultiinstallable"],
        "extension_params": {"project_namespace": project.name},
    }
    response = requests.post(f"{kube_helm_api}/helm-install-chart", json=payload)
