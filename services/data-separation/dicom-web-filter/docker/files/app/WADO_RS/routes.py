import logging
import re
from uuid import UUID

import httpx
from app.crud import BaseDataAdapter, get_project_data_adapter
from app.config import DICOMWEB_BASE_URL
from app.streaming_helpers import metadata_replace_stream
from app.utils import get_user_project_ids
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator, Tuple, List

# Create a router
router = APIRouter()

# Set logging level
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


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


async def stream_multiple_multipart(
    method: str,
    urls: list[str],
    headers: dict,
) -> tuple[str, AsyncGenerator[bytes, None]]:
    """
    Streams multipart responses from multiple URLs. The first response is streamed as-is;
    subsequent responses have their boundary replaced to match the first one's.

    Returns:
        content_type (str): The unified Content-Type header with boundary.
        body (AsyncGenerator[bytes, None]): Streamed multipart body.
    """
    client = httpx.AsyncClient()

    async def combined_stream() -> AsyncGenerator[bytes, None]:
        try:
            # First response: use as-is and extract boundary
            async with client.stream(
                method, urls[0], headers=headers
            ) as first_response:
                first_ct = first_response.headers.get("Content-Type", "")
                match = re.search(r'boundary="?([^";]+)"?', first_ct)
                if not match:
                    raise ValueError("No boundary in first Content-Type header")
                unified_boundary = match.group(1).encode()

                async for chunk in first_response.aiter_bytes():
                    yield chunk

            # Remaining responses: replace boundaries to match the first
            for url in urls[1:]:
                async with client.stream(method, url, headers=headers) as resp:
                    ct = resp.headers.get("Content-Type", "")
                    match = re.search(r'boundary="?([^";]+)"?', ct)
                    if not match:
                        raise ValueError(f"No boundary in Content-Type from {url}")
                    original_boundary = match.group(1).encode()

                    buffer = b""
                    pattern_size = len(original_boundary) + 4
                    async for chunk in resp.aiter_bytes():
                        buffer += chunk
                        buffer = replace_boundary(
                            buffer, original_boundary, unified_boundary
                        )
                        if len(buffer) > pattern_size:
                            yield buffer[:-pattern_size]
                            buffer = buffer[-pattern_size:]
                    if buffer:
                        yield buffer
        finally:
            await client.aclose()

    # Get content-type from first URL
    async with client.stream(method, urls[0], headers=headers) as r:
        content_type = r.headers.get("Content-Type", "application/octet-stream")

    return content_type, combined_stream()


async def stream_passthrough(
    method: str,
    url: str,
    headers: dict,
) -> Tuple[str, AsyncGenerator[bytes, None]]:
    client = httpx.AsyncClient()

    # 1) Build the request
    req = client.build_request(method, url, headers=headers)
    # 2) Send it with streaming turned on
    response = await client.send(req, stream=True)

    if response.status_code not in (200, 204):
        await response.aclose()
        await client.aclose()
        raise httpx.HTTPStatusError(
            f"Upstream returned status {response.status_code} for URL: {url}",
            request=response.request,
            response=response,
        )

    # Grab the full Content-Type (boundary included)
    content_type = response.headers.get(
        "Content-Type",
        headers.get("Content-Type", "application/octet-stream"),
    )

    async def generator():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            # Always close both response *and* client
            await response.aclose()
            await client.aclose()

    return content_type, generator()


def stream_study_metadata(study: str, request: Request) -> StreamingResponse:
    """
    Streams the metadata of a DICOM study from the DICOMWeb server.

    Args:
        study (str): The unique identifier (Study Instance UID) of the DICOM study.
        request (Request): The incoming HTTP request.

    Returns:
        StreamingResponse: A streaming response containing the study metadata in JSON format.
    """
    return StreamingResponse(
        metadata_replace_stream(
            method="GET",
            url=f"{DICOMWEB_BASE_URL}/studies/{study}/metadata",
            request=request,
            search="/".join(DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]).encode(),
            replace=b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}/series/{series}{remaining_path:path}", tags=["WADO-RS"])
async def proxy_series_requests(
    study: str,
    series: str,
    remaining_path: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """
    Proxy any series-level DICOMWeb requests (e.g. including /instances/{instance},
        /metadata, /rendered) with appropriate media types.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for CRUD operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        response: Response object
    """
    is_admin = request.scope.get("admin") is True
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uids=[study],
        series_instance_uids=[series],
    )
    is_mapped = len(data_project_mappings) > 0

    if not (is_admin or is_mapped):
        return Response(status_code=status.HTTP_403_FORBIDDEN)

    # Build the upstream URL
    forward_url = f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}{remaining_path}"

    # Choose how to stream and what content-type to return
    if remaining_path.endswith("/metadata"):
        return StreamingResponse(
            metadata_replace_stream(
                "GET",
                forward_url,
                request=request,
                search="/".join(
                    DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]
                ).encode(),
                replace=b"dicom-web-filter",
            ),
            media_type="application/dicom+json",
        )
    else:
        content_type, body = await stream_passthrough(
            method="GET",
            url=forward_url,
            headers=request.headers,
        )
        return StreamingResponse(
            body,
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": content_type,
            },
        )


@router.get("/studies/{study}/metadata", tags=["WADO-RS"])
async def retrieve_study_metadata(
    study: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
    project_ids_of_user=Depends(get_user_project_ids),
):
    """Retrieve the metadata of the study. If all series of the study are mapped to the project, the metadata is returned. If only some series are mapped, the metadata is filtered and only the mapped series are returned.
       Metadata contains routes to the series and instances of the study. These point to dcm4chee, which is why we need to replace the base URL.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for CRUD operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        StreamingResponse: Response object
    """

    if request.scope.get("admin") is True:
        return stream_study_metadata(study, request)

    # Retrieve series mapped to the project for the given study
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uid=[study],
    )
    mapped_series_uids = set(
        data_project_mapping.series_instance_uid
        for data_project_mapping in data_project_mappings
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(study_instance_uid=study)

    logging.info(f"all_series: {all_series}")

    if set(mapped_series_uids) == set(all_series):
        return stream_study_metadata(study, request)

    async def metadata_generator(search=b"", replace=b""):
        """Used to get the metadata of the series which are mapped to the project. The base URL is replaced in the metadata.

        Args:
            search (bytes, optional): dcm4chee base URL. Defaults to b"".
            replace (bytes, optional): Custom base URL. Defaults to b"".

        Yields:
            bytes: Part of the response stream
        """
        buffer = b""
        pattern_size = len(search)
        async with httpx.AsyncClient() as client:
            for series_uid in mapped_series_uids:
                metadata_response = await client.get(
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}/metadata",
                    headers=dict(request.headers),
                )
                async for chunk in metadata_response.aiter_bytes():
                    buffer += chunk
                    buffer = buffer.replace(search, replace)
                    to_yield = (
                        buffer[:-pattern_size] if len(buffer) > pattern_size else b""
                    )
                    yield to_yield
                    buffer = buffer[-pattern_size:]

        # Yield any remaining buffer after the last chunk
        if buffer:
            yield buffer

    return StreamingResponse(
        metadata_generator(
            "/".join(DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]).encode(),
            b"dicom-web-filter",
        ),
        media_type="application/dicom+json",
    )


@router.get("/studies/{study}{rendered_path:path}", tags=["WADO-RS"])
async def retrieve_study_or_rendered(
    study: str,
    rendered_path: str,
    request: Request,
    crud: BaseDataAdapter = Depends(get_project_data_adapter),
):
    """Retrieve the study from the DICOMWeb server. If all series of the study are mapped to the project, the study is returned. If only some series are mapped, the study is filtered and only the mapped series are returned.
        If there is a rendered path, the rendered study is returned.
    Args:
        study (str): Study Instance UID
        request (Request): Request object
        crud (BaseDataAdapter, optional): Data adapter for CRUD operations. Defaults to Depends(get_project_data_adapter).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [p["id"] for p in request.scope.get("token")["projects"]]

    query_string = request.url.query

    def append_query(url: str) -> str:
        return f"{url}?{query_string}" if query_string else url

    # If user is admin, stream the entire study or rendered
    if request.scope.get("admin") is True:
        forward_url = append_query(
            f"{DICOMWEB_BASE_URL}/studies/{study}{rendered_path}"
        )
        content_type, body = await stream_passthrough(
            method="GET",
            url=forward_url,
            headers=request.headers,
        )
        return StreamingResponse(
            body,
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": content_type,
            },
        )

    # Otherwise, filter series based on project access
    data_project_mappings = await crud.get_data_project_mappings(
        project_ids=project_ids_of_user,
        study_instance_uid=[study],
    )
    mapped_series_uids = set(
        [
            data_project_mappings.series_instance_uid
            for data_project_mappings in data_project_mappings
        ]
    )

    logging.debug(f"mapped_series_uids: {mapped_series_uids}")

    all_series = await crud.get_all_series_of_study(
        study_instance_uid=study,
    )

    logging.debug(f"all_series: {all_series}")
    # If all series are mapped, stream the entire study or rendered
    if set(mapped_series_uids) == set(all_series):
        forward_url = append_query(
            f"{DICOMWEB_BASE_URL}/studies/{study}{rendered_path}"
        )
        content_type, body = await stream_passthrough(
            method="GET",
            url=forward_url,
            headers=request.headers,
        )
        return StreamingResponse(
            body,
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": content_type,
            },
        )

    # Otherwise, build URL list only for allowed series
    forward_urls = [
        append_query(
            f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}{rendered_path}"
        )
        for series_uid in mapped_series_uids
    ]
    content_type, body = await stream_multiple_multipart(
        method="GET",
        urls=forward_urls,
        headers=request.headers,
    )

    return StreamingResponse(
        body,
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": content_type,
        },
    )
