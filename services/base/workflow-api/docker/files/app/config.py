from pydantic_settings import BaseSettings
from celery import Celery
from functools import cached_property

class Settings(BaseSettings):
    DATABASE_URL: str

    @cached_property
    def ASYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    @cached_property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

settings = Settings()