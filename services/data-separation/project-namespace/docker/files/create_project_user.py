import os
from datetime import datetime, timezone

import requests
from kubernetes import client, config
from kaapanapy.logger import get_logger
from KeycloakHelper import KeycloakHelper

logger = get_logger(__name__)


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def update_airflow_managed_namespaces_if_needed():
    if not _bool_env("MANAGED_KUBERNETES"):
        return

    project_namespace = f"project-{os.getenv('PROJECT_NAME')}"
    services_namespace = os.getenv("SERVICES_NAMESPACE")
    configmap_name = os.getenv(
        "AIRFLOW_MANAGED_NAMESPACES_CONFIGMAP", "airflow-managed-namespaces"
    )

    if not all([project_namespace, services_namespace]):
        logger.warning(
            "Skipping Airflow namespace update because Kubernetes API context is incomplete."
        )
        return

    config.load_incluster_config()
    core_v1 = client.CoreV1Api()
    apps_v1 = client.AppsV1Api()

    configmap = core_v1.read_namespaced_config_map(
        name=configmap_name,
        namespace=services_namespace,
    )
    current_value = (configmap.data or {}).get("namespaces", "")
    namespaces = [ns.strip() for ns in current_value.split(",") if ns.strip()]

    if project_namespace in namespaces:
        logger.info(
            "Project namespace %s already present in %s/%s",
            project_namespace,
            services_namespace,
            configmap_name,
        )
        return

    namespaces.append(project_namespace)
    core_v1.patch_namespaced_config_map(
        name=configmap_name,
        namespace=services_namespace,
        body={"data": {"namespaces": ",".join(namespaces)}},
    )
    logger.info(
        "Added project namespace %s to %s/%s",
        project_namespace,
        services_namespace,
        configmap_name,
    )

    apps_v1.patch_namespaced_deployment(
        name="airflow-scheduler",
        namespace=services_namespace,
        body={
            "spec": {
                "template": {
                    "metadata": {
                        "annotations": {
                            "kubectl.kubernetes.io/restartedAt": datetime.now(
                                timezone.utc
                            ).isoformat()
                        }
                    }
                }
            }
        },
    )
    logger.info("Restarted airflow-scheduler to pick up managed namespace changes.")

if __name__ == "__main__":
    kc_client = KeycloakHelper()
    project_user = os.getenv("PROJECT_USER")
    project_user_password = os.getenv("PROJECT_USER_PASSWORD")
    project_name = os.getenv("PROJECT_NAME")
    project_id = os.getenv("project_id")
    user_payload = {
        "username": project_user,
        "credentials": [{"type": "password", "value": project_user_password}],
        "enabled": True,
        "emailVerified": False,
        "firstName": project_user,
        "lastName": "System",
        "email": f"{project_user}@{project_name}.kaapana",
        "requiredActions": [],
        "groups": ["kaapana_user"],
    }
    kc_client.post_user(user_payload, reset_password=True)

    keycloak_user = kc_client.get_user_by_name(project_user)
    keycloak_user_id = keycloak_user.get("id")

    ### Add role mappings to system user in access-information-point
    SERVICE_NAMESPACE = os.getenv("SERVICES_NAMESPACE")
    project_user_role = "principal-investigator"
    response = requests.post(
        f"http://aii-service.{SERVICE_NAMESPACE}.svc:8080/projects/{project_id}/role/{project_user_role}/user/{keycloak_user_id}"
    )
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 409:
            pass
        else:
            logger.error(
                f"Failed to create project mapping in {project_name=} for {project_user=} and {project_user_role=}"
            )
            raise e

    update_airflow_managed_namespaces_if_needed()
