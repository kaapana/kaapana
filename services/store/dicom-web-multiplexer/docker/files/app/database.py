from typing import AsyncGenerator

from fastapi.concurrency import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from .config import DATABASE_URL

async_engine = create_async_engine(DATABASE_URL, echo=True)
async_session = sessionmaker(
    bind=async_engine, expire_on_commit=False, class_=AsyncSession
)

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
