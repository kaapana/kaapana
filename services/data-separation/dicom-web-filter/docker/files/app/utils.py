import logging
from uuid import UUID

import httpx
from app.config import ACCESS_INFORMATION_INTERFACE_HOST

logger = logging.getLogger(__name__)


async def get_default_project_id() -> UUID:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/admin"
        )
    project = response.json()
    return UUID(project["id"])
