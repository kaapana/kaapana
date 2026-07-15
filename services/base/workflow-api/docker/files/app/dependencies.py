import functools
from typing import AsyncGenerator

from app.config import settings
from app.database import async_session
from app.utils import ConnectionManager
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session


## Check if needed TODO
@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def require_dev_mode() -> None:
    if not settings.DEV_MODE:
        raise HTTPException(
            status_code=403,
            detail="Creating new versions of workflows is only allowed when DEV_MODE=True.",
        )
