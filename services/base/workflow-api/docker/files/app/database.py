from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker as async_sessionmaker
from app.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker as sync_sessionmaker


print(settings.ASYNC_DATABASE_URL)
# Async engine for FastAPI (uses asyncpg)
async_engine = create_async_engine(settings.ASYNC_DATABASE_URL, future=True, echo=False)
async_session = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine for Celery (uses psycopg2)
sync_engine = create_engine(settings.SYNC_DATABASE_URL, future=True, echo=False)
sync_session = sync_sessionmaker(
    bind=sync_engine,
    expire_on_commit=False,
)






