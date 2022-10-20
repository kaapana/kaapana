from pydantic import BaseSettings

class Settings(BaseSettings):
    """
    Configuration of the application

    Settings are populated using environment variables
    https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings
    https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names
    """
    kube_helm_url: str
    prometheus_url: str

    minio_url: str
    minio_username: str
    minio_password: str

    keycloak_url: str
    keycloak_admin_username: str
    keycloak_admin_password: str
    
    airflow_url: str = "http://airflow-service.flow.svc:8080/flow/kaapana/api"

settings = Settings()
