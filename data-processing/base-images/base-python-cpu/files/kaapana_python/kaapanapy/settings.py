from typing import Optional
import os
from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings
import warnings


class KaapanaSettings(BaseSettings):
    """
    These settings are imported in every module of the kaapana-pip library
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

@model_validator(mode="after")
def warn_on_default_namespaces(self) -> "KaapanaSettings":
    if (
        os.getenv("KAAPANA_ADMIN_NAMESPACE") is None
        and os.getenv("ADMIN_NAMESPACE") is None
    ):
        warnings.warn(
            "admin_namespace is using default value 'admin'. "
            "Set KAAPANA_ADMIN_NAMESPACE or ADMIN_NAMESPACE explicitly.",
            UserWarning,
            stacklevel=2,
        )
    if (
        os.getenv("KAAPANA_SERVICES_NAMESPACE") is None
        and os.getenv("SERVICES_NAMESPACE") is None
    ):
        warnings.warn(
            "services_namespace is using default value 'services'. "
            "Set KAAPANA_SERVICES_NAMESPACE or SERVICES_NAMESPACE explicitly.",
            UserWarning,
            stacklevel=2,
        )
    return self


class KeycloakSettings(KaapanaSettings):
    keycloak_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_KEYCLOAK_URL", "KEYCLOAK_URL"),
    )
    client_secret: str = Field(
        validation_alias=AliasChoices("KAAPANA_CLIENT_SECRET", "OIDC_CLIENT_SECRET")
    )
    client_id: str = Field("kaapana", validation_alias="KAAPANA_CLIENT_ID")

    @model_validator(mode="after")
    def set_keycloak_url(self) -> "KeycloakSettings":
        if self.keycloak_url is None:
            self.keycloak_url = (
                f"http://keycloak-external-service.{self.admin_namespace}.svc:80"
            )
        return self


class OpensearchSettings(KaapanaSettings):
    """
    Settings for Opensearch module
    """

    opensearch_host: Optional[str] = Field(
        default=None,
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

    @model_validator(mode="after")
    def set_opensearch_host(self) -> "OpensearchSettings":
        if self.opensearch_host is None:
            self.opensearch_host = (
                f"opensearch-service.{self.services_namespace}.svc"
            )
        return self


class ProjectSettings(KaapanaSettings):
    """
    Project specific settings
    """

    project_user_name: str = Field(
        "system", validation_alias="KAAPANA_PROJECT_USER_NAME"
    )
    project_user_password: str = Field(
        validation_alias=AliasChoices(
            "KAAPANA_PROJECT_USER_PASSWORD", "SYSTEM_USER_PASSWORD"
        )
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


class ServicesSettings(KaapanaSettings):
    # ADMIN
    keycloak_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_KEYCLOAK_URL", "KEYCLOAK_URL"),
    )
    kube_helm_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_KUBE_HELM_URL", "KUBE_HELM_URL"),
    )

    # SERVICES
    aii_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_AII_URL", "AII_URL"),
    )
    dicom_web_filter_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "KAAPANA_DICOM_WEB_FILTER_URL", "DICOM_WEB_FILTER_URL"
        ),
    )
    opensearch_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_OPENSEARCH_URL", "OPENSEARCH_URL"),
    )
    kaapana_backend_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_BACKEND_URL"),
    )
    minio_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_MINIO_URL", "MINIO_URL"),
    )
    notification_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("KAAPANA_NOTIFICATION_URL", "NOTIFICATION_URL"),
    )

    @model_validator(mode="after")
    def set_service_urls(self) -> "ServicesSettings":
        a = self.admin_namespace
        s = self.services_namespace
        if self.keycloak_url is None:
            self.keycloak_url = f"http://keycloak-external-service.{a}.svc:80"
        if self.kube_helm_url is None:
            self.kube_helm_url = f"http://kube-helm-service.{a}.svc:5000"
        if self.aii_url is None:
            self.aii_url = f"http://aii-service.{s}.svc:8080"
        if self.dicom_web_filter_url is None:
            self.dicom_web_filter_url = f"http://dicom-web-filter-service.{s}.svc:8080"
        if self.opensearch_url is None:
            self.opensearch_url = f"http://opensearch-service.{s}.svc:9200"
        if self.kaapana_backend_url is None:
            self.kaapana_backend_url = f"http://kaapana-backend-service.{s}.svc:5000"
        if self.minio_url is None:
            self.minio_url = f"http://minio-service.{s}.svc:9000"
        if self.notification_url is None:
            self.notification_url = f"http://notification-service.{s}.svc:80"
        return self
