from typing import Optional

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings


class KaapanaSettings(BaseSettings):
    """
    These settings are imported in every module of the kaapana-pip library
    """

    services_namespace: str = "services"
    admin_namespace: str = "admin"
    kaapana_log_level: str = "DEBUG"
    timezone: str = Field("Europe/Berlin", validation_alias=AliasChoices("TZ"))


class KeycloakSettings(KaapanaSettings):
    keycloak_url: str = "http://keycloak-external-service.admin.svc:80"
    client_secret: str = Field(
        validation_alias=AliasChoices("KAAPANA_CLIENT_SECRET", "OIDC_CLIENT_SECRET")
    )
    client_id: str = Field("kaapana", validation_alias="KAAPANA_CLIENT_ID")


class OpensearchSettings(KaapanaSettings):
    """
    Settings for Opensearch module
    """

    opensearch_host: str = "opensearch-service.services.svc"
    opensearch_port: str = "9200"
    default_index: str = Field(
        "project_admin",
        validation_alias=AliasChoices("KAAPANA_DEFAULT_OPENSEARCH_INDEX"),
    )


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


class ServicesSettings(BaseSettings):
    # ADMIN
    keycloak_url: str
    kube_helm_url: str

    # SERVICES
    aii_url: str
    dicom_web_filter_url: str
    opensearch_url: str
    kaapana_backend_url: str
    minio_url: str
    notification_url: str


class AccessSettings(BaseSettings):
    """
    Settings for accesss control (e.g. AII Interface)
    """
    aii_service_url: str
