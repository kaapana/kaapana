import traceback

import httpx
from app.auth import get_external_token
from app.logger import get_logger
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_204_NO_CONTENT

router = APIRouter()
logger = get_logger(__file__)


async def stream(method, url, query_params=None, headers=None):
    query_params = query_params or {}
    headers = headers or {}

    async with httpx.AsyncClient() as client:
        async with client.stream(
            method, url, params=dict(query_params), headers=dict(headers), timeout=10
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk


async def retrieve_studies(request: Request) -> Response:
    """Retrieve studies from the DICOM Web server.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(method="GET", url=f"{rs_endpoint}/studies", headers=headers),
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
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(method="GET", url=f"{rs_endpoint}/studies/{study}/series", headers=headers),
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
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(method="GET", url=f"{rs_endpoint}/studies/{study}/series/{series}/instances", headers=headers),
        media_type="application/dicom+json",
    )


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    """This endpoint is used to get all studies mapped to the project.

    Args:
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_studies(request=request)


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):
    """This endpoint is used to get all series of a study mapped to the project.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_series(study=study, request=request)


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(
    study: str,
    series: str,
    request: Request,
):
    """This endpoint is used to get all instances of a series mapped to the project.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """
    return await retrieve_instances(study=study, series=series, request=request)
