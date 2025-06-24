from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    airflow_url: str = os.getenv("AIRFLOW_URL")
    services_namespace: str = os.getenv("SERVICES_NAMESPACE")

settings = Settings()
