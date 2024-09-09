from ..database import get_session
from . import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import StreamingResponse
import logging

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

    if await crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
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
    if await crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
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
