import logging
from uuid import UUID

import httpx
from app.crud import BaseDataAdapter
from app.config import DICOMWEB_BASE_URL_WADO_URI
from app.utils import get_user_project_ids, get_project_data_adapter
from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

router = APIRouter()


logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# WADO-RS routes


async def stream_wado(request: Request):
    """Stream the instance from the DICOMWeb server.

    Yields:
        bytes: DICOM instance
    """
    async with httpx.AsyncClient() as client:
        async with client.stream(
            "GET",
            f"{DICOMWEB_BASE_URL_WADO_URI}",
            params=request.query_params,
            headers=dict(request.headers),
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk


@router.get("/wado", tags=["WADO-URI"])
async def retrieve_instance(
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """This endpoint is the wado uri endpoint.

    Args:
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for database operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        StreamingResponse: Response object
    """

    if request.scope.get("admin") is True:
        return StreamingResponse(stream_wado(request=request))

    # Retrieve all studies mapped to the project
    studies = set(await crud.get_all_studies_mapped_to_projects(project_ids_of_user))

    # check if studyUID is in the query parameters
    if "studyUID" in request.query_params:
        # Check if the requested studies are mapped to the project
        requested_studies = set(request.query_params.getlist("studyUID"))
        studies = studies.intersection(requested_studies)

    query_params = dict(request.query_params)
    query_params["studyUID"] = []

    # Add only the studies mapped to the project to the query parameters
    for study_uid in studies:
        query_params["studyUID"].append(study_uid)

    if "seriesUID" in request.query_params:
        series_in_query_params = set(request.query_params.getlist("seriesUID"))

        all_mapped_series = set(
            await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
                project_ids=project_ids_of_user,
                study_instance_uid=list(studies)[
                    0
                ],  # If seriesUID is present, providing multiple studies is not supported (Ambiguity)
            )
        )

        series = all_mapped_series.intersection(series_in_query_params)

        query_params["seriesUID"] = []
        for series_uid in series:
            query_params["seriesUID"].append(series_uid)

    # Update the query parameters
    request._query_params = query_params

    return StreamingResponse(stream_wado(request=request))
