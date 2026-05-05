import os
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from .models import Base

# Async Database URL from environment, e.g., postgresql+asyncpg://user:password@host:port/dbname
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set")


# Async engine for FastAPI (uses asyncpg)
async_engine = create_async_engine(DATABASE_URL, future=True, echo=False)
async_session = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """Create database tables asynchronously based on models."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
