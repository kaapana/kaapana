from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List

import os


class Settings(BaseSettings):
    """
    Configuration of the application

    Settings are populated using environment variables
    https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings
    https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names
    """

    hostname: str
    instance_name: str

    prometheus_url: str

    kaapana_build_timestamp: str
    kaapana_build_version: str
    kaapana_platform_build_branch: str = Field(validation_alias="KAAPANA_BUILD_BRANCH")
    kaapana_platform_last_commit_timestamp: str = Field(
        validation_alias="KAAPANA_LAST_COMMIT_TIMESTAMP"
    )
    kaapana_deployment_timestamp: str = Field(validation_alias="DEPLOYMENT_TIMESTAMP")
    mount_points: List[str] = str(os.getenv("MOUNT_POINTS_TO_MONITOR", "")).split(",")

    minio_url: str
    minio_username: str
    minio_password: str

    keycloak_url: str
    keycloak_admin_username: str
    keycloak_admin_password: str

    traefik_url: str

    airflow_url: str
    services_namespace: str
    admin_namespace: str = Field(validation_alias="ADMIN_NAMESPACE", default="admin")


settings = Settings()
