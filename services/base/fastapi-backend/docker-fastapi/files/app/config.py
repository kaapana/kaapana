
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Configuration of the application

    Settings are populated using environment variables
    https://fastapi.tiangolo.com/advanced/settings/#pydantic-settings
    https://pydantic-docs.helpmanual.io/usage/settings/#environment-variable-names
    """
    airflow_url: str = "http://airflow-service.flow.svc:8080/flow/kaapana/api"

    hostname: str
    node_id: str


settings = Settings()
