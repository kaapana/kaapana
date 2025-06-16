from uuid import UUID
from opensearchpy import OpenSearch

# from kaapanapy.helper import get_opensearch_client
from kaapanapy.settings import OpensearchSettings
from kaapanapy.logger import get_logger
from fastapi import Request
from app.config import ACCESS_INFORMATION_INTERFACE_HOST
import httpx

logger = get_logger(__name__)


def get_opensearch_client(request: Request) -> OpenSearch:
    """
    Create and return an OpenSearch client.
    This function should be implemented to connect to your OpenSearch instance.
    """
    access_token = request.headers.get("x-forwarded-access-token")
    settings = OpensearchSettings()
    auth_headers = {"Authorization": f"Bearer {access_token}"}
    return OpenSearch(
        hosts=[
            {
                "host": settings.opensearch_host,
                "port": settings.opensearch_port,
            }
        ],
        http_compress=True,  # enables gzip compression for request bodies
        use_ssl=True,
        verify_certs=False,
        ssl_assert_hostname=False,
        ssl_show_warn=False,
        timeout=10,
        headers=auth_headers,
    )


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


async def get_project_index_mapping() -> dict[UUID, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects")
    response.raise_for_status()
    projects_info = response.json()
    return {
        UUID(project.get("id")): project.get("opensearch_index")
        for project in projects_info
    }
