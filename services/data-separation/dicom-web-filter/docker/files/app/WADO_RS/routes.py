import binascii
import logging
import os
import re

import httpx
from app import crud
from app.config import DICOMWEB_BASE_URL
from app.database import get_session
from app.streaming_helpers import metadata_replace_stream
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import AsyncGenerator, List

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


def get_boundary() -> bytes:
    """Generate a random boundary for the multipart message.

    Returns:
        bytes: Random boundary
    """
    return binascii.hexlify(os.urandom(16))


async def stream(
    method="GET",
    urls: List[str] = [],
    request_headers: dict = None,
    new_boundary: bytes = None,
) -> AsyncGenerator[bytes, None]:
    """Stream the data to the DICOMWeb server. The boundary in the multipart message is replaced. We use this to set a custom boundary which is then also present in the headers.
       There was a problem with the original boundary not being present in the headers, which is why we need to replace it.
       There was a problem with the boundary being split across chunks, which is why we need to buffer the data and replace the boundary in the buffer.

    Args:
        method (str, optional): _description_. Defaults to "GET".
        urls List of url(str): _description_. Defaults to empty list.
        request_headers (dict, optional): _description_. Defaults to None.
        new_boundary (bytes, optional): _description_. Defaults to None.

    Yields:
        _type_: _description_
    """
    async with httpx.AsyncClient() as client:
        for url in urls:
            try:
                async with client.stream(
                    method, url, headers=dict(request_headers)
                ) as response:
                    if response.status_code != 200:
                        logging.warning(
                            f"Upstream returned status {response.status_code} for URL: {url}"
                        )
                        raise httpx.HTTPStatusError(
                            f"Upstream returned status {response.status_code}",
                            request=response.request,
                            response=response,
                        )
                    content_type = response.headers.get("Content-Type")
                    if not content_type or "boundary=" not in content_type:
                        logging.error(
                            f"Missing or invalid Content-Type header: {content_type}"
                        )
                        raise ValueError(
                            f"Invalid or missing Content-Type header: {content_type}"
                        )

                    match = re.search(b"boundary=(.*)", content_type.encode())
                    if not match:
                        if new_boundary:
                            logging.error(
                                f"Boundary not found in Content-Type header: {content_type}"
                            )
                            raise ValueError(
                                f"Boundary not found in header: {content_type}"
                            )
                        buffer = None
                    else:
                        response_boundary = match.group(1)
                        buffer = b""
                        # Size of the boundary pattern (2 bytes for "--", (16 bytes for the boundary) and 2 bytes for "--"" at the end)
                        pattern_size = len(new_boundary) + 4

                    logging.debug(
                        f"Streaming response from {url} with boundary replacement."
                    )

                    async for chunk in response.aiter_bytes():
                        logging.debug(f"Received chunk of size {len(chunk)}")
                        if new_boundary:
                            buffer += chunk

                            buffer = replace_boundary(
                                buffer=buffer,
                                old_boundary=response_boundary,
                                new_boundary=new_boundary,
                            )

                            if len(buffer) > pattern_size:
                                to_yield = buffer[:-pattern_size]
                                yield to_yield
                                buffer = buffer[-pattern_size:]
                        else:
                            yield chunk

                    if buffer:
                        yield buffer

            except httpx.RequestError as e:
                logging.error(f"Request error while connecting to {url}: {e}")
                raise
            except Exception as e:
                logging.exception(f"Unexpected error during streaming from {url}: {e}")
                raise


def stream_study(study: str, request: Request) -> StreamingResponse:
    """
    Streams a DICOM study from a remote DICOMweb server.

    This function sends a GET request to retrieve a study from the DICOMweb server
    and returns a streaming response to the client. The response is sent using
    chunked transfer encoding with a multipart/related content type.

    Args:
        study (str): The unique identifier (Study Instance UID) of the DICOM study to retrieve.
        request (Request): The incoming HTTP request, used to pass headers.

    Returns:
        StreamingResponse: A streaming response containing the DICOM study data.
    """

    boundary = get_boundary()
    return StreamingResponse(
        stream(
            method="GET",
            urls=[f"{DICOMWEB_BASE_URL}/studies/{study}"],
            request_headers=request.headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


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


def stream_study_rendered(study: str, request: Request) -> StreamingResponse:
    """
    Streams a rendered representation of a DICOM study from the DICOMWeb server.

    Args:
        study (str): The unique identifier (Study Instance UID) of the DICOM study.
        request (Request): The incoming HTTP request.

    Returns:
        StreamingResponse: A streaming response containing the rendered study data.
    """

    boundary = get_boundary()
    return StreamingResponse(
        stream(
            method="GET",
            urls=[f"{DICOMWEB_BASE_URL}/studies/{study}/rendered"],
            request_headers=request.headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


async def stream_rendered(
    method="GET", url: str = None, request_headers: dict = None, new_boundary=None
):
    """
    Asynchronously streams a rendered DICOM series or instance from the DICOMWeb server.

    Args:
        method (str, optional): The HTTP method to use (default is "GET").
        url (str, optional): The target URL for the request.
        request_headers (dict, optional): The request headers.
        new_boundary (optional): Custom boundary for multipart response.

    Yields:
        bytes: Chunks of the streamed response.
    """

    async with httpx.AsyncClient() as client:
        async with client.stream(
            method=method, url=url, headers=request_headers, timeout=10
        ) as response:
            response.raise_for_status()
            async for chunk in response.aiter_bytes():
                yield chunk


# WADO-RS routes
@router.get("/studies/{study}", tags=["WADO-RS"])
async def retrieve_study(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):
    """Retrieve the study from the DICOMWeb server. If all series of the study are mapped to the project, the study is returned. If only some series are mapped, the study is filtered and only the mapped series are returned.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    if request.scope.get("admin") is True:
        return stream_study(study, request)

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
            session=session, project_ids=project_ids_of_user, study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

    logging.info(f"all_series: {all_series}")

    # check if all series of the study are mapped to the project
    if set(mapped_series_uids) == set(all_series):
        return stream_study(study, request)

    boundary = get_boundary()
    forward_urls = []
    for series_uid in mapped_series_uids:
        forward_urls.append(f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}")
    return StreamingResponse(
        stream(
            method="GET",
            urls=forward_urls,
            request_headers=request.headers,
            new_boundary=boundary,
        ),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


@router.get("/studies/{study}/series/{series}{remaining_path:path}", tags=["WADO-RS"])
async def proxy_series_requests(
    study: str,
    series: str,
    remaining_path: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """
    Proxy any series-level DICOMWeb requests (e.g. including /instances/{instance},
        /metadata, /rendered) with appropriate media types.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    is_admin = request.scope.get("admin") is True
    is_mapped = await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    )

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
        boundary = get_boundary()
        return StreamingResponse(
            stream(
                method="GET",
                urls=[forward_url],
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )


@router.get("/studies/{study}/metadata", tags=["WADO-RS"])
async def retrieve_study_metadata(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):
    """Retrieve the metadata of the study. If all series of the study are mapped to the project, the metadata is returned. If only some series are mapped, the metadata is filtered and only the mapped series are returned.
       Metadata contains routes to the series and instances of the study. These point to dcm4chee, which is why we need to replace the base URL.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get("admin") is True:
        return stream_study_metadata(study, request)

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
            session=session, project_ids=project_ids_of_user, study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

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


@router.get("/studies/{study}/rendered", tags=["WADO-RS"])
async def retrieve_study_rendered(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):
    """Retrieve the study from the DICOMWeb server. If all series of the study are mapped to the project, the study is returned. If only some series are mapped, the study is filtered and only the mapped series are returned.

    Args:
        study (str): Study Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    if request.scope.get("admin") is True:
        return stream_study_rendered(study, request)

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_projects(
            session=session, project_ids=project_ids_of_user, study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

    logging.info(f"all_series: {all_series}")

    if set(mapped_series_uids) == set(all_series):
        return stream_study_rendered(study, request)

    async def stream_filtered_series():
        """Stream the series which are mapped to the project. The boundary in the multipart message is replaced, because each response has its own boundary.

        Yields:
            bytes: Part of the response stream
        """
        first_boundary = None
        first_series = True
        async with httpx.AsyncClient() as client:
            for series_uid in mapped_series_uids:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}/rendered",
                    headers=dict(request.headers),
                ) as response:

                    # If the series has incompatible media type, skip it
                    if response.status_code == 406:
                        continue

                    try:
                        if first_series:
                            boundary = first_boundary = re.search(
                                b"boundary=(.*)",
                                response.headers["Content-Type"].encode(),
                            ).group(1)
                            first_series = False
                        else:

                            boundary = re.search(
                                b"boundary=(.*)",
                                response.headers["Content-Type"].encode(),
                            ).group(1)
                    except:
                        continue

                    async for chunk in response.aiter_bytes():
                        # if boundary is not first_boundary: replace the boundary
                        if boundary != first_boundary:
                            chunk = replace_boundary(
                                buffer=chunk,
                                old_boundary=boundary,
                                new_boundary=first_boundary,
                            )
                        yield chunk

    return StreamingResponse(stream_filtered_series())
