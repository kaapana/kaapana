import traceback

import httpx
from app.auth import get_external_token
from app.logger import get_logger
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

from ..SUPPLEMENTS.routes import fetch_thumbnail_async

logger = get_logger(__file__)

router = APIRouter()


async def stream(method, url, query_params=None, headers=None):
    query_params = query_params or {}
    headers = headers or {}

    async with httpx.AsyncClient() as client:
        async with client.stream(
            method, url, params=dict(query_params), headers=dict(headers), timeout=10
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk


@router.get("/studies/{study}", tags=["WADO-RS"])
async def retrieve_studies(
    study: str,
    request: Request,
):
    """Retrieve the series from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
    Returns:
        StreamingResponse: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "multipart/related"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}",
            headers=headers,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related;",
        },
    )


@router.get("/studies/{study}/series/{series}", tags=["WADO-RS"])
async def retrieve_series(
    study: str,
    series: str,
    request: Request,
):
    """Retrieve the series from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
    Returns:
        StreamingResponse: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "multipart/related"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}",
            headers=headers,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related;",
        },
    )


@router.get("/studies/{study}/series/{series}/instances/{instance}", tags=["WADO-RS"])
async def retrieve_instances(
    study: str,
    series: str,
    instance: str,
    request: Request,
):
    """Retrieve the instance from the DICOMWeb server. If the series which the instance belongs to is mapped to the project, the instance is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object
    Returns:
        StreamingResponse: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "multipart/related"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}",
            headers=headers,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related;",
        },
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
    tags=["WADO-RS"],
)
async def retrieve_frames(
    study: str,
    series: str,
    instance: str,
    frames: str,
    request: Request,
):
    """Retrieve the frames from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        frames (str): Frame numbers
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """
    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "multipart/related"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
            headers=headers,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related;",
        },
    )


# Routes for retrieve modifiers


@router.get("/studies/{study}/metadata", tags=["WADO-RS"])
async def retrieve_studies_metadata(
    study: str,
    request: Request,
):
    """Retrieve the metadata of the instance.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/metadata",
            headers=headers,
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}/series/{series}/metadata", tags=["WADO-RS"])
async def retrieve_series_metadata(
    study: str,
    series: str,
    request: Request,
):
    """Retrieve the metadata of the instance.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/metadata",
            headers=headers,
        ),
        media_type="application/dicom+json",
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/metadata", tags=["WADO-RS"]
)
async def retrieve_instances_metadata(
    study: str,
    series: str,
    instance: str,
    request: Request,
):
    """Retrieve the metadata of the instance.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object

    Returns:
        response: Response object
    """

    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)

    logger.info(request.headers)
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom+json"}

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/metadata",
            headers=headers,
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}/rendered", tags=["WADO-RS"])
async def retrieve_series_rendered(
    study: str,
    request: Request,
):
    """Retrieve the series from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """
    try:
        # Get Google OAuth token
        token = await get_external_token(request)

        # Construct the URL to the DICOMWeb server
        rs_endpoint = rs_endpoint_url(
            request
        )  # Assuming this function retrieves the DICOMWeb endpoint
        url = f"{rs_endpoint}/studies/{study}/rendered"

        # Fetch the thumbnail asynchronously
        return await fetch_thumbnail_async(url, token)

    except Exception as e:
        logger.error("Error while retrieving instance rendered image")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(
            content="Not implemented by endpoint: {request.state.endpoint}",
            status_code=500,
        )


@router.get("/studies/{study}/series/{series}/rendered", tags=["WADO-RS"])
async def retrieve_series_rendered(
    study: str,
    series: str,
    request: Request,
):
    """Retrieve the series from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """
    try:
        # Get Google OAuth token
        token = await get_external_token(request)

        # Construct the URL to the DICOMWeb server
        rs_endpoint = rs_endpoint_url(
            request
        )  # Assuming this function retrieves the DICOMWeb endpoint
        url = f"{rs_endpoint}/studies/{study}/series/{series}/rendered"

        # Fetch the thumbnail asynchronously
        return await fetch_thumbnail_async(url, token)

    except Exception as e:
        logger.error("Error while retrieving instance rendered image")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(
            content="Not implemented by endpoint: {request.state.endpoint}",
            status_code=500,
        )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/rendered", tags=["WADO-RS"]
)
async def retrieve_instance_rendered(
    study: str,
    series: str,
    instance: str,
    request: Request,
):
    """Retrieve the instance rendered image from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """
    try:
        # Get Google OAuth token
        token = await get_external_token(request)

        # Construct the URL to the DICOMWeb server
        rs_endpoint = rs_endpoint_url(
            request
        )  # Assuming this function retrieves the DICOMWeb endpoint
        url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"

        # Fetch the thumbnail asynchronously
        return await fetch_thumbnail_async(url, token)

    except Exception as e:
        logger.error("Error while retrieving instance rendered image")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Internal server error", status_code=500)
        # Fetch the thumbnail asynchronously
        return await fetch_thumbnail_async(url, token)

    except Exception as e:
        logger.error("Error while retrieving instance rendered image")
        logger.error(e)
        logger.error(traceback.format_exc())
        return Response(content="Internal server error", status_code=500)
