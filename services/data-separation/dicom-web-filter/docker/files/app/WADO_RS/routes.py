from ..database import get_session
from . import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL
from sqlalchemy.ext.asyncio import AsyncSession
import re
import httpx
from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import StreamingResponse
import logging

# Create a router
router = APIRouter()

# Set logging level
logging.basicConfig(level=logging.INFO)


async def stream(method="GET", url=None, request_headers=None):
    async with httpx.AsyncClient() as client:
        async with client.stream(
            method,
            url,
            headers=dict(request_headers),
        ) as response:
            async for chunk in response.aiter_bytes():
                yield chunk


# WADO-RS routes
@router.get("/studies/{study}", tags=["WADO-RS"])
async def retrieve_study(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
            session=session, project_id=DEFAULT_PROJECT_ID, study_instance_uid=study
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

        return StreamingResponse(
            stream("GET", f"{DICOMWEB_BASE_URL}/studies/{study}", request.headers),
            media_type="application/dicom",
        )

    async def stream_multiple_series():
        first_boundary = None
        first_series = True
        buffer = b""  # Initialize an empty buffer
        pattern_size = 20  # Size of the boundary pattern (2 bytes for "--", 16 bytes for the boundary and 2 bytes for "--"" at the end)
        async with httpx.AsyncClient() as client:
            for series_uid in mapped_series_uids:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}",
                    headers=dict(request.headers),
                ) as response:
                    if first_series:
                        boundary = first_boundary = re.search(
                            b"boundary=(.*)", response.headers["Content-Type"].encode()
                        ).group(1)
                        first_series = False
                    else:
                        boundary = re.search(
                            b"boundary=(.*)", response.headers["Content-Type"].encode()
                        ).group(1)

                    async for chunk in response.aiter_bytes():
                        buffer += chunk
                        # Process the buffer
                        if boundary != first_boundary:
                            buffer = buffer.replace(
                                f"--{boundary.decode()}\r\n".encode(),
                                f"--{first_boundary.decode()}\r\n".encode(),
                            ).replace(
                                f"\r\n--{boundary.decode()}--".encode(),
                                f"\r\n--{first_boundary.decode()}--".encode(),
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

    return StreamingResponse(stream_multiple_series(), media_type="application/dicom")


@router.get("/studies/{study}/series/{series}", tags=["WADO-RS"])
async def retrieve_series(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):

    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}",
                request_headers=request.headers,
            ),
            media_type="application/dicom",
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

    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}",
                request_headers=request.headers,
            ),
            media_type="application/dicom",
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
    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        # Set the content type to multipart/related
        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
                request_headers=request.headers,
            ),
            media_type="multipart/related",
        )
    else:
        return Response(status_code=204)


# Routes for retrieve modifiers


@router.get("/studies/{study}/metadata", tags=["WADO-RS"])
async def retrieve_study_metadata(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
            session=session, project_id=DEFAULT_PROJECT_ID, study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

    logging.info(f"all_series: {all_series}")

    if set(mapped_series_uids) == set(all_series):
        StreamingResponse(
            stream(
                "GET", f"{DICOMWEB_BASE_URL}/studies/{study}/metadata", request.headers
            ),
            media_type="application/dicom+json",
        )

    async def metadata_generator():
        async with httpx.AsyncClient() as client:
            for series_uid in mapped_series_uids:
                metadata_response = await client.get(
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series_uid}/metadata",
                    headers=dict(request.headers),
                )
                async for chunk in metadata_response.aiter_bytes():
                    yield chunk

    return StreamingResponse(metadata_generator(), media_type="application/dicom+json")


@router.get("/studies/{study}/series/{series}/metadata", tags=["WADO-RS"])
async def retrieve_series_metadata(
    study: str,
    series: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
):

    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return StreamingResponse(
            stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/metadata",
                request.headers,
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

    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return StreamingResponse(
            stream(
                "GET",
                f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/metadata",
                request.headers,
            ),
            media_type="application/dicom+json",
        )
    else:
        return Response(status_code=204)


@router.get("/studies/{study}/rendered", tags=["WADO-RS"])
async def retrieve_study_rendered(
    study: str, request: Request, session: AsyncSession = Depends(get_session)
):

    # Retrieve series mapped to the project for the given study
    mapped_series_uids = (
        await crud.get_series_instance_uids_of_study_which_are_mapped_to_project(
            session=session, project_id=DEFAULT_PROJECT_ID, study_instance_uid=study
        )
    )

    logging.info(f"mapped_series_uids: {mapped_series_uids}")

    # get all series of the study
    all_series = await crud.get_all_series_of_study(
        session=session, study_instance_uid=study
    )

    logging.info(f"all_series: {all_series}")

    if set(mapped_series_uids) == set(all_series):
        return StreamingResponse(
            stream(
                "GET", f"{DICOMWEB_BASE_URL}/studies/{study}/rendered", request.headers
            ),
            media_type="multipart/related",
        )
    # TODO: Adjust the boundary for the multipart message

    async def stream_filtered_series():
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
                            chunk = chunk.replace(
                                f"--{boundary.decode()}\r\n".encode(),
                                f"--{first_boundary.decode()}\r\n".encode(),
                            ).replace(
                                f"\r\n--{boundary.decode()}--".encode(),
                                f"\r\n--{first_boundary.decode()}--".encode(),
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
    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):
        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/rendered",
                request_headers=request.headers,
            ),
            media_type="multipart/related",
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

    if crud.check_if_series_in_given_study_is_mapped_to_project(
        session=session,
        project_id=DEFAULT_PROJECT_ID,
        study_instance_uid=study,
        series_instance_uid=series,
    ):

        return StreamingResponse(
            stream(
                method="GET",
                url=f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/rendered",
                request_headers=request.headers,
            )
        )

    else:
        return Response(status_code=204)
