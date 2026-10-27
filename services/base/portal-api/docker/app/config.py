from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    CACHE_TTL_SECONDS: int = 10
    LOG_LEVEL: str = "INFO"
    # comma-separated; empty: all namespaces (needs a ClusterRole)
    INGRESS_NAMESPACES: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
