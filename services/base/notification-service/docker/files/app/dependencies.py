import functools
from typing import AsyncGenerator

from app.database import async_session
from app.utils import ConnectionManager
from kaapanapy.services.AccessService import AccessService
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_access_service() -> AccessService:
    return AccessService()
