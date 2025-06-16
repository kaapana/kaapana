import logging
from uuid import UUID

import httpx
from app.crud import BaseDataAdapter, get_project_data_adapter
from app.config import DICOMWEB_BASE_URL
from app.utils import get_user_project_ids
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
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uids=[study],
        series_instance_uids=[series],
    )
    if request.scope.get("admin") is True or (len(data_project_mappings) > 0):

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
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uids=[study],
        series_instance_uids=[series],
    )
    if request.scope.get("admin") is True or (len(data_project_mappings) > 0):

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
