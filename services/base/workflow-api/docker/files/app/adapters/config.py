from pydantic_settings import BaseSettings
from functools import cached_property


class Settings(BaseSettings):
    DATABASE_URL: str
    AIRFLOW_URL: str | None = None

    @cached_property
    def ASYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    @cached_property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)


settings = Settings()
