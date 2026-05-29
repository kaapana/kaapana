from functools import lru_cache
from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class KaapanaSettings(BaseSettings):
    """
    Base settings
    """

    services_namespace: str = Field(
        default="services",
        validation_alias=AliasChoices(
            "KAAPANA_SERVICES_NAMESPACE", "SERVICES_NAMESPACE"
        ),
    )
    admin_namespace: str = Field(
        default="admin",
        validation_alias=AliasChoices("KAAPANA_ADMIN_NAMESPACE", "ADMIN_NAMESPACE"),
    )
    kaapana_log_level: str = Field(
        default="DEBUG", validation_alias=AliasChoices("KAAPANA_LOG_LEVEL")
    )
    timezone: str = Field(
        "Europe/Berlin",
        validation_alias=AliasChoices("TZ", "KAAPANA_TIMEZONE", "TIMEZONE"),
    )


class KeycloakSettings(KaapanaSettings):
    keycloak_url: str = Field(
        default="http://keycloak-external-service.admin.svc:80",
        validation_alias=AliasChoices("KAAPANA_KEYCLOAK_URL", "KEYCLOAK_URL"),
    )
    client_secret: str = Field(
        validation_alias=AliasChoices("KAAPANA_CLIENT_SECRET", "OIDC_CLIENT_SECRET")
    )
    client_id: str = Field("kaapana", validation_alias="KAAPANA_CLIENT_ID")


class OpensearchSettings(KaapanaSettings):
    """
    Settings for Opensearch module
    """

    opensearch_host: str = Field(
        default="opensearch-service.services.svc",
        validation_alias=AliasChoices("KAAPANA_OPENSEARCH_HOST", "OPENSEARCH_HOST"),
    )
    opensearch_port: str = Field(
        default="9200",
        validation_alias=AliasChoices("KAAPANA_OPENSEARCH_PORT", "OPENSEARCH_PORT"),
    )
    default_index: str = Field(
        "project_admin",
        validation_alias=AliasChoices(
            "KAAPANA_DEFAULT_OPENSEARCH_INDEX", "DEFAULT_INDEX"
        ),
    )


class ProjectSettings(KaapanaSettings):
    """
    Project specific settings
    """

    project_user_name: str = Field(
        "system", validation_alias="KAAPANA_PROJECT_USER_NAME"
    )
    project_user_password: Optional[str] = Field(
        validation_alias=AliasChoices(
            "KAAPANA_PROJECT_USER_PASSWORD", "SYSTEM_USER_PASSWORD"
        )
    )
    project_id: Optional[str] = Field(
        None, validation_alias=AliasChoices("KAAPANA_PROJECT_ID")
    )


class OperatorSettings(BaseSettings):
    """
    General variables available in all processing-containers.
    """

    run_id: str
    dag_id: str
    task_id: str
    workflow_dir: str
    batch_name: str = "batch"
    operator_out_dir: str
    batches_input_dir: str
    operator_in_dir: Optional[str] = None


class ServicesSettings(BaseSettings):
    # ADMIN
    keycloak_url: str = Field(
        default="http://keycloak-external-service.admin.svc:80",
        validation_alias=AliasChoices("KAAPANA_KEYCLOAK_URL", "KEYCLOAK_URL"),
    )
    kube_helm_url: str = Field(
        default="http://kube-helm-service.admin.svc:5000",
        validation_alias=AliasChoices("KAAPANA_KUBE_HELM_URL", "KUBE_HELM_URL"),
    )

    # SERVICES
    aii_url: str = Field(
        default="http://aii-service.services.svc:8080",
        validation_alias=AliasChoices("KAAPANA_AII_URL", "AII_URL"),
    )
    dicom_web_filter_url: str = Field(
        default="http://dicom-web-filter-service.services.svc:8080",
        validation_alias=AliasChoices(
            "KAAPANA_DICOM_WEB_FILTER_URL", "DICOM_WEB_FILTER_URL"
        ),
    )
    opensearch_url: str = Field(
        default="http://opensearch-service.services.svc:9200",
        validation_alias=AliasChoices("KAAPANA_OPENSEARCH_URL", "OPENSEARCH_URL"),
    )
    kaapana_backend_url: str = Field(
        default="http://kaapana-backend-service.services.svc:5000",
        validation_alias=AliasChoices("KAAPANA_BACKEND_URL"),
    )
    minio_url: str = Field(
        default="http://minio-service.services.svc:9000",
        validation_alias=AliasChoices("KAAPANA_MINIO_URL", "MINIO_URL"),
    )
    notification_url: str = Field(
        default="http://notification-service.services.svc:80",
        validation_alias=AliasChoices("KAAPANA_NOTIFICATION_URL", "NOTIFICATION_URL"),
    )

    traefik_url: str = Field(
        "https://traefik-0.admin.svc:443",
        validation_alias=AliasChoices("KAAPANA_TRAEFIK_URL"),
    )


@lru_cache
def get_kaapana_settings() -> KaapanaSettings:
    return KaapanaSettings()


@lru_cache
def get_keycloak_settings() -> KeycloakSettings:
    return KeycloakSettings()


@lru_cache
def get_opensearch_settings() -> OpensearchSettings:
    return OpensearchSettings()


@lru_cache
def get_project_settings() -> ProjectSettings:
    return ProjectSettings()


@lru_cache
def get_operator_settings() -> OperatorSettings:
    return OperatorSettings()


@lru_cache
def get_services_settings() -> ServicesSettings:
    return ServicesSettings()
