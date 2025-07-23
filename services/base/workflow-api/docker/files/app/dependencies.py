import functools
from typing import AsyncGenerator

from app.database import async_session
from app.utils import ConnectionManager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request
import json


async def get_async_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
# async def get_session() -> AsyncGenerator[AsyncSession, None]:
#     async with async_session() as session:
#         yield session

## Check if needed TODO
@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


def get_forwarded_headers(request: Request):
    forwarded_headers = {
        "X-Forwarded-Preferred-Username": request.headers.get("x-forwarded-preferred-username"),
        "X-Forwarded-Email": request.headers.get("x-forwarded-email"),
    }
    
    return forwarded_headers


# TODO: move that to kaapanapy since it is used in multiple places
def get_project(request: Request):
    project = request.headers.get("Project")
    print(f"Project header: {project}")
    if not project:
        raise ValueError("Project header is required")
    return json.loads(project)

def get_project_id(request: Request):
    project = get_project(request)
    return project.get("id")
