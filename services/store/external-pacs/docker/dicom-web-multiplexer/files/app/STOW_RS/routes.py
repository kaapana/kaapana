from app.logger import get_logger
from fastapi import APIRouter, Request, Response
from app.auth import authorize_headers
from app.utils import rs_endpoint_url

import httpx
from app import config

from fastapi.responses import Response

router = APIRouter()
logger = get_logger(__name__)


@router.delete("/studies/{study}", tags=["STOW-RS"])
async def delete_study(study, request: Request):
    """Deletes a specific study from the DICOMWeb server.

    Args:
        study (str): The Study Instance UID of the study to delete.
        request (Request): The incoming HTTP request containing authorization headers and endpoint information.

    Returns:
        Response: The HTTP response from the DICOMWeb server.
    """
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}"

    auth_headers = authorize_headers(request)

    headers = {"Content-Type": "application/dicom+json; charset=utf-8", **auth_headers}

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
    return response


@router.delete("/studies/{study}/series/{series}", tags=["STOW-RS"])
async def delete_study(study, series, request: Request):
    """Deletes a specific series within a study from the DICOMWeb server.

    Args:
        study (str): The Study Instance UID of the study containing the series.
        series (str): The Series Instance UID of the series to delete.
        request (Request): The incoming HTTP request containing authorization headers and endpoint information.

    Returns:
        Response: The HTTP response from the DICOMWeb server.
    """
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}"

    auth_headers = authorize_headers(request)

    headers = {"Content-Type": "application/dicom+json; charset=utf-8", **auth_headers}

    async with httpx.AsyncClient() as client:
        response = await client.delete(url, headers=headers)
    return response


async def __stream_data(request: Request, url: str = f"/studies"):
    """Streams data to the DICOMWeb server.

    Args:
        request (Request): The incoming HTTP request containing the data to be streamed.
        url (str, optional): The endpoint URL to stream the data to. Defaults to "/studies".

    Raises:
        HTTPError: If the request to the DICOMWeb server fails.
    """
    auth_headers = authorize_headers(request)

    async def data_streamer():
        async for chunk in request.stream():
            yield chunk

    async with httpx.AsyncClient(timeout=500) as client:
        async with client.stream(
            "POST",
            f"{config.DICOMWEB_BASE_URL}/{url}",
            content=data_streamer(),
            headers=auth_headers,
        ) as response:
            response.raise_for_status()


@router.post("/studies", tags=["STOW-RS"])
async def store_instances(request: Request):
    """Stores instances to the DICOMWeb server.

    Args:
        request (Request): The incoming HTTP request containing the instances to be stored.

    Returns:
        Response: An HTTP response with status code 200 upon successful storage.
    """
    await __stream_data(request, url=f"studies")

    return Response(status_code=200)
