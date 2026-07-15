import json
import logging
from urllib.parse import unquote
from typing import List
from uuid import UUID

import httpx
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from app import crud
from app.config import ACCESS_INFORMATION_INTERFACE_HOST, DICOMWEB_BASE_URL

logger = logging.getLogger(__name__)

MAX_UIDS_IN_GET = 100  # ~40 chars per UID + URL encoding => ~4,000 characters


async def get_default_project_id() -> UUID:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/admin"
        )
    project = response.json()
    return UUID(project["id"])


async def assert_project_not_archived(project_id: UUID) -> None:
    """
    Raise 403 if the project is archived in AII.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/{project_id}"
        )
    response.raise_for_status()
    if response.json().get("is_archived"):
        raise HTTPException(
            status_code=403,
            detail=f"Project {project_id} is archived (read-only).",
        )


async def get_project_name_by_id(project_id: UUID) -> str | None:
    """Return the name of a project by its ID, or None if not found.

    Args:
        project_id (UUID): The project ID to look up.

    Returns:
        str | None: The project name, or None if the request fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/{project_id}"
        )
    if not response.is_success:
        return None
    return response.json().get("name")


async def get_project_short_id_by_id(project_id: UUID) -> str | None:
    """Return the short_id of a project by its ID, or None if not found.

    Args:
        project_id (UUID): The project ID to look up.

    Returns:
        str | None: The project short_id, or None if the request fails.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/{project_id}"
        )
    if not response.is_success:
        return None
    return response.json().get("short_id")


def get_user_project_ids(request: Request) -> list[UUID]:
    """Get the project IDs of the projects the user is associated with."""
    return [UUID(project["id"]) for project in request.scope.get("token")["projects"]]


def get_project_id_from_cookie(request: Request) -> UUID | None:
    """Extract the selected project UUID from the 'Project' browser cookie.

    The Kaapana frontend stores the active project as JSON: {"name": "...", "id": "<uuid>"}.
    Returns None if the cookie is absent or malformed.
    """
    raw = request.cookies.get("Project")
    if not raw:
        return None
    try:
        return UUID(json.loads(unquote(raw))["id"])
    except (json.JSONDecodeError, KeyError, ValueError):
        logger.warning("Could not parse Project cookie: %r", raw)
        return None


async def get_filtered_studies_mapped_to_projects(
    request: Request,
    session: AsyncSession,
    project_ids_of_user: str,
    study_uid_param_name: str,
) -> List[str]:

    if study_uid_param_name in request.query_params:
        # Check if the requested studies are mapped to the project
        requested_studies = request.query_params.getlist(study_uid_param_name)
        studies = await crud.get_mapped_studies_by_project_and_study_uids(
            session, project_ids_of_user, requested_studies
        )

    else:
        # Step 1: Count how many studies are mapped to this user's projects
        study_count = await crud.count_studies_mapped_to_projects(
            session, project_ids_of_user
        )
        if study_count == 0:
            return []
        # Retrieve studies mapped to the project
        elif study_count <= MAX_UIDS_IN_GET:
            studies = set(
                await crud.get_all_studies_mapped_to_projects(
                    session, project_ids_of_user
                )
            )
        else:
            # Too many UIDs to include in GET — use PACS filter first
            # Call PACS with original filters
            async with httpx.AsyncClient() as client:
                pacs_response = await client.get(
                    f"{DICOMWEB_BASE_URL}/studies",
                    params=request.query_params,
                    headers=dict(request.headers),
                )

            if pacs_response.status_code == HTTP_204_NO_CONTENT:
                return []

            response_data = pacs_response.content
            studies_json = pacs_response.json()

            requested_studies = set()
            for study in studies_json:
                study_uid = study.get("0020000D", {}).get(  # Tag for StudyInstanceUID
                    "Value", [None]
                )[0]
                requested_studies.add(study_uid)
            # filter project specific
            studies = await crud.get_mapped_studies_by_project_and_study_uids(
                session, project_ids_of_user, requested_studies
            )
            if len(studies) > MAX_UIDS_IN_GET:
                logging.warning(
                    f"Filtered study count ({len(studies)}) exceeds safe GET URL limit ({MAX_UIDS_IN_GET}). "
                    "Consider applying more specific query parameters (e.g. StudyDate, Modality) to narrow the result set."
                )
    return studies
