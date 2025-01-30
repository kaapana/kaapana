import binascii
import os
import re

import httpx
from app.auth import authorize_headers, get_external_token
from app.logger import get_logger
from app.utils import rs_endpoint_url
from app.streaming_helpers import metadata_replace_stream

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

logger = get_logger(__file__)

router = APIRouter()


def replace_boundary(buffer: bytes, old_boundary: bytes, new_boundary: bytes) -> bytes:
    """Replace the boundary in the buffer.

    Args:
        buffer (bytes): Buffer
        old_boundary (bytes): Old boundary
        new_boundary (bytes): New boundary

    Returns:
        bytes: Buffer with replaced boundary
    """
    return buffer.replace(
        f"--{old_boundary.decode()}".encode(),
        f"--{new_boundary.decode()}".encode(),
    ).replace(
        f"--{old_boundary.decode()}--".encode(),
        f"--{new_boundary.decode()}--".encode(),
    )


def get_boundary() -> bytes:
    """Generate a random boundary for the multipart message.

    Returns:
        bytes: Random boundary
    """
    return binascii.hexlify(os.urandom(16))


async def stream(method, url, request_headers, new_boundary):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method, url, headers=dict(request_headers)
        ) as response:
            # Check if the Content-Type header contains a boundary
            content_type = response.headers.get("Content-Type", "").encode()
            boundary_match = re.search(b"boundary=(.*)", content_type)

            if boundary_match:
                # Boundary found, proceed with boundary replacement logic
                response_boundary = boundary_match.group(1)
                buffer = b""  # Buffer to ensure the boundary is not split across chunks
                pattern_size = (
                    len(new_boundary) + 4
                )  # 2 bytes for "--" at the start and 2 bytes for "--" at the end

                async for chunk in response.aiter_bytes():
                    buffer += chunk
                    # Replace the boundary in the buffer
                    buffer = replace_boundary(
                        buffer=buffer,
                        old_boundary=response_boundary,
                        new_boundary=new_boundary,
                    )
                    to_yield = (
                        buffer[:-pattern_size] if len(buffer) > pattern_size else b""
                    )
                    yield to_yield
                    buffer = buffer[-pattern_size:]

                # Yield any remaining buffer after the last chunk
                if buffer:
                    yield buffer
            else:
                # No boundary found, stream the response as-is
                async for chunk in response.aiter_bytes():
                    yield chunk


async def stream_direct(method, url, headers=None):
    headers = headers or {}

    async with httpx.AsyncClient() as client:
        async with client.stream(
            method, url, headers=dict(headers), timeout=10
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk


def stream_study(url: str, headers: dict) -> StreamingResponse:
    boundary = get_boundary()
    return StreamingResponse(
        stream(
            method="GET",
            url=url,
            request_headers=headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


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
    auth_headers = {"Authorization": f"Bearer {token}"}
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}"
    return stream_study(url, auth_headers)


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
    auth_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": 'multipart/related; type="application/dicom"; transfer-syntax=*',
    }
    rs_endpoint = rs_endpoint_url(request)
    boundary = get_boundary()

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}",
            request_headers=auth_headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
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
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/dicom; transfer-syntax=*"}
    boundary = get_boundary()

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}",
            request_headers=headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/frames/{frame}",
    tags=["WADO-RS"],
)
async def retrieve_frames(
    study: str,
    series: str,
    instance: str,
    frame: str,
    request: Request,
):
    """Retrieve the frames from the DICOMWeb server.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        frame (str): Frame numbers
        request (Request): Request object

    Returns:
        StreamingResponse: Response object
    """

    token = await get_external_token(request)
    rs_endpoint = rs_endpoint_url(request)
    headers = {"Authorization": f"Bearer {token}"}
    boundary = get_boundary()

    return StreamingResponse(
        stream(
            method="GET",
            url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/frames/{frame}",
            request_headers=headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


# METADATA
def stream_metadata(url, request_headers, query_params):
    dicom_web_base_url = url.split("/studies")[0]
    return StreamingResponse(
        metadata_replace_stream(
            "GET",
            url,
            headers=request_headers,
            query_params=query_params,
            search="/".join(dicom_web_base_url.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


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

    auth_headers = await authorize_headers(request)
    rs_endpoint = rs_endpoint_url(request)

    return stream_metadata(
        url=f"{rs_endpoint}/studies/{study}/metadata",
        request_headers=auth_headers,
        query_params=request.query_params,
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
    auth_headers = await authorize_headers(request)
    rs_endpoint = rs_endpoint_url(request)

    return stream_metadata(
        url=f"{rs_endpoint}/studies/{study}/series/{series}/metadata",
        request_headers=auth_headers,
        query_params=request.query_params,
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
    auth_headers = await authorize_headers(request)
    rs_endpoint = rs_endpoint_url(request)

    return stream_metadata(
        url=f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/metadata",
        request_headers=auth_headers,
        query_params=request.query_params,
    )


# RENDERED
async def stream_rendered(url: str, headers: dict):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method="GET", url=url, headers=headers, timeout=10
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk


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
    token = await get_external_token(request)
    auth_headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/rendered"
    return StreamingResponse(stream_rendered(url, auth_headers))


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
    token = await get_external_token(request)
    auth_headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}/rendered"
    return StreamingResponse(stream_rendered(url, auth_headers))


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
    token = await get_external_token(request)
    auth_headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/rendered"
    return StreamingResponse(stream_rendered(url, auth_headers))


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/frames/{frame}/rendered",
    tags=["WADO-RS"],
)
async def retrieve_frame_rendered(
    study: str,
    series: str,
    instance: str,
    frame: str,
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
    token = await get_external_token(request)
    auth_headers = {"Authorization": f"Bearer {token}", "Accept": "image/png"}
    rs_endpoint = rs_endpoint_url(request)
    url = f"{rs_endpoint}/studies/{study}/series/{series}/instances/{instance}/frames/{frame}/rendered"
    return StreamingResponse(stream_rendered(url, auth_headers))
