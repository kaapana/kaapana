from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the storage-api.

    The service holds no static store credentials: it forwards the caller's
    access token to each store (DICOMweb bearer / MinIO web-identity).
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    dicom_wadors_endpoint: str = ""
    dicom_stowrs_endpoint: str = ""
    minio_url: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
