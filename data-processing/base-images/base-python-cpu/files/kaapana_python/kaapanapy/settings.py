from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings


class KaapanaSettings(BaseSettings):
    """
    These settings are imported in every module of the kaapana-pip library
    """

    services_namespace: str = "services"
    admin_namespace: str = "admin"
    kaapana_log_level: str = "DEBUG"


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
    default_index: str = "project_1"


class ProjectSettings(KaapanaSettings):
    """
    Project specific settings
    """

    project_name: str = Field("admin", validation_alias="KAAPANA_PROJECT_NAME")
    project_user_name: str = Field(
        "system", validation_alias="KAAPANA_PROJECT_USER_NAME"
    )
    project_user_password: str = Field(
        validation_alias=AliasChoices(
            "KAAPANA_PROJECT_USER_PASSWORD", "SYSTEM_USER_PASSWORD"
        )
    )
