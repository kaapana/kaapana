from pydantic import BaseSettings
import os


class Settings(BaseSettings):
    airflow_url: str = os.getenv("AIRFLOW_URL")
    services_namespace: str = os.getenv("SERVICES_NAMESPACE")
    dcm4chee_url: str = os.getenv("DCM4CHEE_URL")

settings = Settings()
