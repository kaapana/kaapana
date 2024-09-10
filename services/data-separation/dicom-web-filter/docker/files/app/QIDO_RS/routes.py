import httpx
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.status import HTTP_204_NO_CONTENT

from .. import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL
from ..database import get_session
from ..streaming_helpers import metadata_replace_stream

router = APIRouter()


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request, session: AsyncSession = Depends(get_session)):
    """This endpoint is used to get all studies mapped to the project.

    Args:
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """

    if "SeriesInstanceUID" in request.query_params:
        # retrieve series mapped to the project
        series = set(
            await crud.get_all_series_mapped_to_project(session, DEFAULT_PROJECT_ID)
        )

        # Check if the requested series are mapped to the project
        requested_series = set(request.query_params.getlist("SeriesInstanceUID"))
        series = series.intersection(requested_series)

        # Remove SeriesInstanceUID from the query parameters
        query_params = dict(request.query_params)
        query_params["SeriesInstanceUID"] = []

        # Add the series mapped to the project to the query parameters
        for uid in series:
            query_params["SeriesInstanceUID"].append(uid)

        # Update the query parameters
        request._query_params = query_params

        if not series:
            # return empty response with status code 204
            return Response(status_code=HTTP_204_NO_CONTENT)

    # check if StudyInstanceUID is in the query parameters
    if "StudyInstanceUID" in request.query_params:

        # Retrieve studies mapped to the project
        studies = set(
            await crud.get_all_studies_mapped_to_project(session, DEFAULT_PROJECT_ID)
        )

        # Check if the requested studies are mapped to the project
        requested_studies = set(request.query_params.getlist("StudyInstanceUID"))
        studies = studies.intersection(requested_studies)

        # Remove StudyInstanceUID from the query parameters
        query_params = dict(request.query_params)
        query_params["StudyInstanceUID"] = []

        # Add the studies mapped to the project to the query parameters
        for uid in studies:
            query_params["StudyInstanceUID"].append(uid)

        # Update the query parameters
        request._query_params = query_params

        if not studies:
            # return empty response with status code 204
            return Response(status_code=HTTP_204_NO_CONTENT)

    # Perform a HEAD request to check the response code without retrieving the body
    async with httpx.AsyncClient() as client:
        response = await client.head(
            f"{DICOMWEB_BASE_URL}/studies",
            params=dict(request.query_params),
            headers=dict(request.headers),
        )

        if response.status_code == 204:
            # Return empty response with status code 204
            return Response(status_code=HTTP_204_NO_CONTENT)

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
    """This endpoint is used to get all series of a study mapped to the project.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """

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

    # Perform a HEAD request to check the response code without retrieving the body
    async with httpx.AsyncClient() as client:
        response = await client.head(
            f"{DICOMWEB_BASE_URL}/studies",
            params=dict(request.query_params),
            headers=dict(request.headers),
        )

        if response.status_code == 204:
            # Return empty response with status code 204
            return Response(status_code=HTTP_204_NO_CONTENT)

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
    """This endpoint is used to get all instances of a series mapped to the project.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """

    query_params = dict(request.query_params)

    # If StudyInstanceUID is in the query parameters, remove it
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # If SeriesInstanceUID is in the query parameters, remove it
    if "SeriesInstanceUID" in query_params:
        query_params.pop("SeriesInstanceUID")

    # Update the query parameters
    request._query_params = query_params

    if not await crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Perform a HEAD request to check the response code without retrieving the body
    async with httpx.AsyncClient() as client:
        response = await client.head(
            f"{DICOMWEB_BASE_URL}/studies",
            params=dict(request.query_params),
            headers=dict(request.headers),
        )

        if response.status_code == 204:
            # Return empty response with status code 204
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
