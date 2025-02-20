import binascii
import logging
import os
import re

import httpx
from app import crud
from app.config import DICOMWEB_BASE_URL
from app.database import get_session
from app.streaming_helpers import metadata_replace_stream
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

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
    url: str = None,
    request_headers: dict = None,
    new_boundary: bytes = None,
):
    """Stream the data to the DICOMWeb server. The boundary in the multipart message is replaced. We use this to set a custom boundary which is then also present in the headers.
       There was a problem with the original boundary not being present in the headers, which is why we need to replace it.
       There was a problem with the boundary being split across chunks, which is why we need to buffer the data and replace the boundary in the buffer.

    Args:
        method (str, optional): _description_. Defaults to "GET".
        url (str, optional): _description_. Defaults to None.
        request_headers (dict, optional): _description_. Defaults to None.
        new_boundary (bytes, optional): _description_. Defaults to None.

    Yields:
        _type_: _description_
    """
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method, url, headers=dict(request_headers)
        ) as response:
            # Boundary has to be replaced
            buffer = b""  # We need the buffer, to ensure the boundary is not being split across chunks
            pattern_size = (
                len(new_boundary) + 4
            )  # 2 bytes for "--" at the start and 2 bytes for "--" at the end
            first_chunk = True
            response_boundary = None
            async for chunk in response.aiter_bytes():
                # Get the boundary which will be replaced from the first chunk
                if first_chunk:
                    response_boundary = re.search(
                        b"boundary=(.*)", response.headers["Content-Type"].encode()
                    ).group(1)
                    first_chunk = False
                buffer += chunk
                # Replace the boundary in the buffer
                buffer = replace_boundary(
                    buffer=buffer,
                    old_boundary=response_boundary,
                    new_boundary=new_boundary,
                )
                to_yield = buffer[:-pattern_size] if len(buffer) > pattern_size else b""
                yield to_yield
                buffer = buffer[-pattern_size:]

            # Yield any remaining buffer after the last chunk
            if buffer:
                yield buffer



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
            url=f"{DICOMWEB_BASE_URL}/studies/{study}",
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
            url=f"{DICOMWEB_BASE_URL}/studies/{study}/rendered",
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

    async def stream_multiple_series(new_boundary: bytes = None):
        """Get the subset if series of the study which are mapped to the project as a stream. The boundary in the multipart message is replaced, because each response has its own boundary.

        Args:
            new_boundary (bytes, optional): Our custom boundary. Defaults to None.

        Yields:
            bytes: Part of the response stream
        """
        buffer = b""  # Initialize an empty buffer
        pattern_size = 20  # Size of the boundary pattern (2 bytes for "--", 16 bytes for the boundary and 2 bytes for "--"" at the end)
        async with httpx.AsyncClient() as client:
            for series_uid in mapped_series_uids:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}",
                    headers=dict(request.headers),
                ) as response:

                    boundary = re.search(
                        b"boundary=(.*)", response.headers["Content-Type"].encode()
                    ).group(1)

                    async for chunk in response.aiter_bytes():
                        buffer += chunk

                        # Process the buffer
                        buffer = replace_boundary(
                            buffer=buffer,
                            old_boundary=boundary,
                            new_boundary=new_boundary,
                        )

                        # Decide how much of the buffer to yield and retain
                        to_yield = (
                            buffer[:-pattern_size]
                            if len(buffer) > pattern_size
                            else b""
                        )
                        yield to_yield
                        buffer = buffer[
                            -pattern_size:
                        ]  # Retain this much of the buffer

            # Yield any remaining buffer after the last chunk
            if buffer:
                yield buffer

    boundary = get_boundary()

    return StreamingResponse(
        stream_multiple_series(new_boundary=boundary),
        headers={
            "Transfer-Encoding": "chunked",
            "Content-Type": f"multipart/related; boundary={boundary.decode()}",
        },
    )


@router.get("/studies/{study}/series/{series}", tags=["WADO-RS"])
async def retrieve_series(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the series from the DICOMWeb server. If the series is mapped to the project, the series is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        boundary = get_boundary()

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}",
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )

    else:

        return Response(status_code=204)


@router.get("/studies/{study}/series/{series}/instances/{instance}", tags=["WADO-RS"])
async def retrieve_instance(
    study: str,
    series: str,
    instance: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the instance from the DICOMWeb server. If the series which the instance belongs to is mapped to the project, the instance is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        boundary = get_boundary()

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}",
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )

    else:

        return Response(status_code=204)


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
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the frames from the DICOMWeb server. If the series which the instance belongs to is mapped to the project, the frames are returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        frames (str): Frame numbers
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        boundary = get_boundary()

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )
    else:
        return Response(status_code=204)


# Routes for retrieve modifiers


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


@router.get("/studies/{study}/series/{series}/metadata", tags=["WADO-RS"])
async def retrieve_series_metadata(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the metadata of the series. If the series is mapped to the project, the metadata is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return StreamingResponse(
            metadata_replace_stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/metadata",
                request=request,
                search="/".join(
                    DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]
                ).encode(),
                replace=b"dicom-web-filter",
            ),
            media_type="application/dicom+json",
        )
    else:
        return Response(status_code=204)


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/metadata", tags=["WADO-RS"]
)
async def retrieve_instance_metadata(
    study: str,
    series: str,
    instance: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the metadata of the instance. If the series which the instance belongs to is mapped to the project, the metadata is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        response: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return StreamingResponse(
            metadata_replace_stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/metadata",
                request=request,
                search="/".join(
                    DICOMWEB_BASE_URL.split(":")[-1].split("/")[1:]
                ).encode(),
                replace=b"dicom-web-filter",
            ),
            media_type="application/dicom+json",
        )
    else:
        return Response(status_code=204)


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


@router.get("/studies/{study}/series/{series}/rendered", tags=["WADO-RS"])
async def retrieve_series_rendered(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the series from the DICOMWeb server. If the series is mapped to the project, the series is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        boundary = get_boundary()

        return StreamingResponse(
            stream_rendered(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/rendered",
                request_headers=request.headers,
            ),
            media_type="multipart/related",
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )

    else:
        return Response(status_code=204)


@router.get(
    "/studies/{study}/series/{series}/instances/{instance}/rendered", tags=["WADO-RS"]
)
async def retrieve_instance_rendered(
    study: str,
    series: str,
    instance: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the instance from the DICOMWeb server. If the series which the instance belongs to is mapped to the project, the instance is returned. If the series is not mapped, a 204 status code is returned.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        instance (str): SOP Instance UID
        request (Request): Request object
        session (AsyncSession, optional): Database session. Defaults to Depends(get_session).

    Returns:
        StreamingResponse: Response object
    """

    # Get the project IDs of the projects the user is associated with
    project_ids_of_user = [
        project["id"] for project in request.scope.get("token")["projects"]
    ]

    if request.scope.get(
        "admin"
    ) is True or await crud.check_if_series_in_given_study_is_mapped_to_projects(
        session=session,
        project_ids=project_ids_of_user,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        boundary = get_boundary()
        return StreamingResponse(
            stream_rendered(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/rendered",
                request_headers=request.headers,
                new_boundary=boundary,
            ),
            headers={
                "Transfer-Encoding": "chunked",
                "Content-Type": f"multipart/related; boundary={boundary.decode()}",
            },
        )

    else:
        return Response(status_code=204)
