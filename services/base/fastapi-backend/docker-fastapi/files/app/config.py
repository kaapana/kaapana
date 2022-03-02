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
    minio_access_key: str
    minio_secret_key: str

settings = Settings()