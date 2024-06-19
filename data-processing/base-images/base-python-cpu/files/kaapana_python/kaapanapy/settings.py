from pydantic import BaseSettings
import os


class KaapanaSettings(BaseSettings):
    """
    These settings are imported in every module of the kaapana-pip library
    """

    hostname: str = os.getenv("HOSTNAME")
    instance_name: str = os.getenv("INSTANCE_NAME")
    services_namespace: str = os.getenv("SERVICES_NAMESPACE")
    admin_namespace: str = os.getenv("ADMIN_NAMESPACE", "admin")
    kaapana_log_level: str = os.getenv("KAAPANA_LOG_LEVEL", "DEBUG")


class KeycloakSettings(KaapanaSettings):
    keycloak_url: str = os.getenv(
        "KEYCLOAK_URL", "http://keycloak-external-service.admin.svc:80"
    )
    client_secret: str = os.getenv("KAAPANA_CLIENT_SECRET")
    client_id: str = os.getenv("KAAPANA_CLIENT_ID", "kaapana")


class MinioSettings(KaapanaSettings):
    minio_url: str
    minio_username: str
    minio_password: str


class OpensearchSettings(KaapanaSettings):
    """
    Settings for Opensearch module
    """

    opensearch_host: str = os.getenv("OPENSEARCH_HOST")
    opensearch_port: str = os.getenv("OPENSEARCH_PORT")


class ProjectSettings(KaapanaSettings):
    """
    Project specific settings
    """

    project_name: str = os.getenv("KAAPANA_PROJECT_NAME", "admin_project")
    project_user_name: str = os.getenv("KAAPANA_PROJECT_USER_NAME", "system")
    project_user_password: str = os.getenv("KAAPANA_PROJECT_USER_PASSWORD")
