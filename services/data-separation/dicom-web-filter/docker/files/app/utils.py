import logging
from typing import List

import httpx
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from app import crud
from app.config import ACCESS_INFORMATION_INTERFACE_HOST, DICOMWEB_BASE_URL

logger = logging.getLogger(__name__)

MAX_UIDS_IN_GET = 100  # ~40 chars per UID + URL encoding => ~4,000 characters


async def get_default_project_id() -> int:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{ACCESS_INFORMATION_INTERFACE_HOST}/projects/admin"
        )
    project = response.json()
    return int(project["id"])


def get_user_project_ids(request: Request) -> list[int]:
    """Get the project IDs of the projects the user is associated with."""
    return [int(project["id"]) for project in request.scope.get("token")["projects"]]


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
