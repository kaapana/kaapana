from pydantic import BaseSettings
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

    prometheus_url: str = os.getenv("PROMETHEUS_URL")

    kaapana_build_version: str = os.getenv("PROMETHEUS_URL")
    kaapana_build_version: str = os.getenv("PROMETHEUS_URL")

    kaapana_build_timestamp: str = os.getenv("KAAPANA_BUILD_TIMESTAMP")
    kaapana_build_version: str = os.getenv("KAAPANA_BUILD_VERSION")
    kaapana_platform_build_branch: str = os.getenv("KAAPANA_BUILD_BRANCH")
    kaapana_platform_last_commit_timestamp: str = os.getenv(
        "KAAPANA_LAST_COMMIT_TIMESTAMP"
    )
    kaapana_deployment_timestamp: str = os.getenv("DEPLOYMENT_TIMESTAMP")
    mount_points: list[str] = str(os.getenv("MOUNT_POINTS_TO_MONITOR")).split(",")

    minio_url: str
    minio_username: str
    minio_password: str

    keycloak_url: str
    keycloak_admin_username: str
    keycloak_admin_password: str

    traefik_url: str

    airflow_url: str = os.getenv("AIRFLOW_URL")
    services_namespace: str = os.getenv("SERVICES_NAMESPACE")
    admin_namespace: str = os.getenv("ADMIN_NAMESPACE", "admin")


settings = Settings()
