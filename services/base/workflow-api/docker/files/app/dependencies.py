import functools
from typing import AsyncGenerator

from app.database import async_session
from app.utils import ConnectionManager
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


## Check if needed TODO
@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()
