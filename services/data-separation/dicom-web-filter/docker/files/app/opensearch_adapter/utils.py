from uuid import UUID
from opensearchpy import OpenSearch

from kaapanapy.helper import get_opensearch_client
from fastapi import Request
from app.config import ACCESS_INFORMATION_INTERFACE_HOST
import httpx


def get_opensearch(request: Request) -> OpenSearch:
    """
    Create and return an OpenSearch client.
    This function should be implemented to connect to your OpenSearch instance.
    """
    access_token = request.scope.get("token", {}).get("access_token")
    return get_opensearch_client(access_token=access_token)


async def get_project_index(project_id: UUID) -> str:
    """
    Return the index name for a given project.
    This function should be implemented to return the correct index name based on the project ID.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/{project_id}"
        )
    response.raise_for_status()
    project_info = response.json()
    return project_info.get("opensearch_index")


async def get_project_indices(project_ids: list[UUID]) -> list[str]:
    """
    Return the index names for a list of project IDs.
    """
    project_indices = []
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects")
    response.raise_for_status()
    projects_info = response.json()
    for project in projects_info:
        if UUID(project.get("opensearch_index")) in project_ids:
            project_indices.append(project.get("opensearch_index"))

    return project_indices
