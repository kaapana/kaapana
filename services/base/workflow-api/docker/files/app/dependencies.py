import functools
from typing import AsyncGenerator,Dict, Any

from app.database import async_session
from app.utils import ConnectionManager
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Request, HTTPException, status

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
def get_project(request: Request) -> Dict[str, Any]:
    """Get project from request headers"""
    project = request.headers.get("Project")
    if not project:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project header is required"
        )
    return json.loads(project)

def get_project_id(request: Request):
    project = get_project(request)
    return project.get("id")
