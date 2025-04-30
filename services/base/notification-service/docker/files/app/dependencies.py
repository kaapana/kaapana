from app.database import async_session
from app.utils import AiiHelper, ConnectionManager
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator
import functools


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_aii_helper() -> AiiHelper:
    return AiiHelper()
