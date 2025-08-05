from pydantic_settings import BaseSettings
from celery import Celery
from functools import cached_property

class Settings(BaseSettings):
    DATABASE_URL: str
    CELERY_BROKER_URL: str
    AIRFLOW_URL: str

    @cached_property
    def ASYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

    @cached_property
    def SYNC_DATABASE_URL(self) -> str:
        return self.DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

settings = Settings()

# Celery Configuration
celery_app = Celery(
    'workflow_engine',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_BROKER_URL,
    include=['app.services.celery']  # Module containing your tasks
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=7 * 24 * 60 * 60,  # 7 days
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,  # Important for long-running tasks
    worker_max_tasks_per_child=1000,  # Restart workers periodically
)