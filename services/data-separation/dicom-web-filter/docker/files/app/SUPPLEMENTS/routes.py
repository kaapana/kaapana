import logging

import httpx
from app import crud
from app.config import DICOMWEB_BASE_URL
from app.database import get_session
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

# Create a router
router = APIRouter()

# Set logging level
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


# Supplement 203: Thumbnail Resources for DICOMweb
@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/thumbnail", tags=["WADO-RS"]
)
async def retrieve_instance_thumbnail(
    study: str,
    series: str,
    instance: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]
    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        async def stream_thumbnail():
            """Stream the thumbnail from the DICOMWeb server.

            Yields:
                bytes: DICOM instance
            """
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/thumbnail",
                    params=request.query_params,
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_thumbnail())

    else:
        return Response(status_code=204)


@router.get("/studies/{study}/series/{series}/thumbnail", tags=["WADO-RS"])
async def retrieve_series_thumbnail(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]
    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        async def stream_thumbnail():
            """Stream the thumbnail from the DICOMWeb server.

            Yields:
                bytes: DICOM instance
            """
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/thumbnail",
                    params=request.query_params,
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_thumbnail())

    else:
        return Response(status_code=204)
