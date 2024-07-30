from fastapi import APIRouter, Request, Depends, Response
from starlette.status import HTTP_204_NO_CONTENT
from ..database import get_session
from . import crud
from ..config import DICOMWEB_BASE_URL, DEFAULT_PROJECT_ID
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.responses import StreamingResponse
import httpx

router = APIRouter()


async def metadata_replace_stream(
    method: str = "GET",
    url: str = None,
    request: Request = None,
    search: bytes = None,
    replace: bytes = None,
):
    buffer = b""
    pattern_size = len(search)
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method,
            url,
            params=dict(request.query_params),
            headers=dict(request.headers),
        ) as response:
            async for chunk in response.aiter_bytes():
                buffer += chunk
                # Process the buffer
                buffer = buffer.replace(search, replace)
                to_yield = buffer[:-pattern_size] if len(buffer) > pattern_size else b""
                yield to_yield
                buffer = buffer[-pattern_size:]  # Retain this much of the buffer

            # Yield any remaining buffer after the last chunk
            if buffer:
                yield buffer


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request, session: AsyncSession = Depends(get_session)):

    # Retrieve studies mapped to the project
    studies = set(
        await crud.get_all_studies_mapped_to_project(session, DEFAULT_PROJECT_ID)
    )

    # check if StudyInstanceUID is in the query parameters
    if "StudyInstanceUID" in request.query_params:
        # Check if the requested studies are mapped to the project
        requested_studies = set(request.query_params.getlist("StudyInstanceUID"))
        studies = studies.intersection(requested_studies)

    if not studies:
        # return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Remove StudyInstanceUID from the query parameters
    query_params = dict(request.query_params)
    query_params["StudyInstanceUID"] = []

    # Add the studies mapped to the project to the query parameters
    for uid in studies:
        query_params["StudyInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{DICOMWEB_BASE_URL}/studies",
            request=request,
            search="/".join(DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # If StudyInstanceUID is in the query parameters, remove it
    query_params = dict(request.query_params)
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = set(
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
            session=session, project_id=DEFAULT_PROJECT_ID, study_instance_uid=study
        )
    )

    # check if SeriesInstanceUID is in the query parameters
    if "SeriesInstanceUID" in request.query_params:
        # Check if the requested series are mapped to the project
        requested_series = set(request.query_params.getlist("SeriesInstanceUID"))
        mapped_series_uids = mapped_series_uids.intersection(requested_series)

    if not mapped_series_uids:
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Remove SeriesInstanceUID from the query parameters
    query_params["SeriesInstanceUID"] = []

    # Add the series mapped to the project to the query parameters
    for uid in mapped_series_uids:
        query_params["SeriesInstanceUID"].append(uid)

    # Update the query parameters
    request._query_params = query_params

    # Send the request to the DICOM Web server
    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{DICOMWEB_BASE_URL}/studies/{study}/series",
            request=request,
            search="/".join(DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):

    query_params = dict(request.query_params)

    # If StudyInstanceUID is in the query parameters, remove it
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # If SeriesInstanceUID is in the query parameters, remove it
    if "SeriesInstanceUID" in query_params:
        query_params.pop("SeriesInstanceUID")

    # Update the query parameters
    request._query_params = query_params

    if not crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Send the request to the DICOM Web server
    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances",
            request=request,
            search="/".join(DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )
