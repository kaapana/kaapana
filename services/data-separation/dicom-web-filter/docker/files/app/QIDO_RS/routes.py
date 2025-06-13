import logging
from uuid import UUID

import httpx
from app.crud import BaseDataAdapter
from app.config import DICOMWEB_BASE_URL
from app.streaming_helpers import metadata_replace_stream
from app.utils import get_user_project_ids, get_project_data_adapter
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_204_NO_CONTENT

router = APIRouter()


async def head_request(url: str, request: Request) -> Response:
    """Perform a HEAD request to check the response code without retrieving the body.
    This is a current workaround to catch 204 responses, which are turned into 200 responses by the StreamingResponse.
    Will change in the future.

    Args:
        url (str): URL to send the request to
        request (Request): Request object

    Returns:
        Response: Response object
    """
    async with httpx.AsyncClient() as client:
        response = await client.head(
            url,
            params=dict(request.query_params),
            headers=dict(request.headers),
        )

    response.raise_for_status()
    return response


async def retrieve_studies(request: Request) -> Response:
    """Retrieve studies from the DICOM Web server.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    # Perform a HEAD request to check the response code without retrieving the body
    head_response = await head_request(f"{DICOMWEB_BASE_URL}/studies", request)

    if head_response.status_code == HTTP_204_NO_CONTENT:
        # If the response is 204 No Content, return it directly
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


async def retrieve_series(study: str, request: Request) -> Response:
    """Retrieve series from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    # Perform a HEAD request to check the response code without retrieving the body
    head_response = await head_request(
        f"{DICOMWEB_BASE_URL}/studies/{study}/series", request
    )

    if head_response.status_code == HTTP_204_NO_CONTENT:
        # If the response is 204 No Content, return it directly
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


async def retrieve_instances(study: str, series: str, request: Request) -> Response:
    """Retrieve instances from the DICOM Web server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        Response: Response object
    """
    # Perform a HEAD request to check the response code without retrieving the body
    head_response = await head_request(
        f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances", request
    )

    if head_response.status_code == HTTP_204_NO_CONTENT:
        # If the response is 204 No Content, return it directly
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


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """This endpoint is used to get all studies mapped to the project.

    Args:
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for CRUD operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        response: Response object
    """

    if request.scope.get("admin") is True:
        return await retrieve_studies(request=request)

    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user
    )

    if "SeriesInstanceUID" in request.query_params:
        # retrieve series mapped to the project
        series = set(
            data_project_mapping.series_instance_uid
            for data_project_mapping in data_project_mappings
        )

        # Check if the requested series are mapped to the project
        requested_series = set(request.query_params.getlist("SeriesInstanceUID"))
        series = series.intersection(requested_series)

        if not series:
            # return empty response with status code 204
            return Response(status_code=HTTP_204_NO_CONTENT)

        # Remove SeriesInstanceUID from the query parameters
        request.query_params["SeriesInstanceUID"] = []

        # Add the series mapped to the project to the query parameters
        for uid in series:
            request.query_params["SeriesInstanceUID"].append(uid)

    # Retrieve studies mapped to the project
    studies = set(
        data_project_mapping.study_instance_uid
        for data_project_mapping in data_project_mappings
    )

    # Update the query parameters
    if not studies:
        # return empty response with status code 204
        return Response(status_code=HTTP_204_NO_CONTENT)

    # Remove StudyInstanceUID from the query parameters
    request.query_params["StudyInstanceUID"] = []
    # Add the studies mapped to the project to the query parameters
    for uid in studies:
        request.query_params["StudyInstanceUID"].append(uid)

    return await retrieve_studies(request=request)


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(
    study: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """This endpoint is used to get all series of a study mapped to the project.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    if request.scope.get("admin") is True:
        return await retrieve_series(study=study, request=request)

    # If StudyInstanceUID is in the query parameters, remove it
    query_params = dict(request.query_params)
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # Retrieve series mapped to the project for the given study
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uids=[study],
    )
    mapped_series_uids = set(
        [
            data_project_mappings.series_instance_uid
            for data_project_mappings in data_project_mappings
        ]
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

    return await retrieve_series(study=study, request=request)


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(
    study: str,
    series: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """This endpoint is used to get all instances of a series mapped to the project.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for CRUD operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        response: Response object
    """

    if request.scope.get("admin") is True:
        return await retrieve_instances(study=study, series=series, request=request)

    query_params = dict(request.query_params)

    # If StudyInstanceUID is in the query parameters, remove it
    if "StudyInstanceUID" in query_params:
        query_params.pop("StudyInstanceUID")

    # If SeriesInstanceUID is in the query parameters, remove it
    if "SeriesInstanceUID" in query_params:
        query_params.pop("SeriesInstanceUID")

    # Update the query parameters
    request._query_params = query_params

    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uids=[study],
        series_instance_uids=[series],
    )

    if not (len(data_project_mappings) > 0):
        return Response(status_code=HTTP_204_NO_CONTENT)

    return await retrieve_instances(study=study, series=series, request=request)
