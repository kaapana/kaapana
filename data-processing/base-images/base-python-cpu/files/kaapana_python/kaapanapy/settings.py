from pydantic import BaseSettings
import os


class KaapanaSettings(BaseSettings):
    """
    These settings are imported in every module of the kaapana-pip library

    Settings are populated using environment variables
    https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings
    https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names
    """

    hostname: str = os.getenv("HOSTNAME")
    instance_name: str = os.getenv("INSTANCE_NAME")
    services_namespace: str = os.getenv("SERVICES_NAMESPACE")
    admin_namespace: str = os.getenv("ADMIN_NAMESPACE", "admin")


class KeycloakSettings(KaapanaSettings):
    keycloak_url: str
    keycloak_admin_username: str
    keycloak_admin_password: str


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
