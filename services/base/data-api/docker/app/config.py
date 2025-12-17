from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/data"
    ARTIFACTS_DIR: str = "./artifacts"


@lru_cache
def get_settings() -> Settings:
    return Settings()
