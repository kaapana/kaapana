import logging
from typing import List
from uuid import UUID

import httpx
from app.config import ACCESS_INFORMATION_INTERFACE_HOST

from fastapi import Request

logger = logging.getLogger(__name__)

MAX_UIDS_IN_GET = 100  # ~40 chars per UID + URL encoding => ~4,000 characters


async def get_default_project_id() -> UUID:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/admin"
        )
    project = response.json()
    return UUID(project["id"])


def get_user_project_ids(request: Request) -> list[UUID]:
    """Get the project IDs of the projects the user is associated with."""
    return [UUID(project["id"]) for project in request.scope.get("token")["projects"]]
