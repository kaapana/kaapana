from ..proxy_request import proxy_request
from ..database import get_session
from . import crud
from ..config import DEFAULT_PROJECT_ID, DICOMWEB_BASE_URL
from sqlalchemy.ext.asyncio import AsyncSession
import re
import httpx
import debugpy
from fastapi import APIRouter, Request, Depends, Response
from fastapi.responses import StreamingResponse

import logging

# Create a router
router = APIRouter()

# Set logging level
logging.basicConfig(level=logging.INFO)

# WADO-RS routes

# debugpy.listen(("localhost", 17777))
# debugpy.wait_for_client()


# def _encode_multipart_message(
#     data: Sequence[bytes],
#     boundary: str = None,
# ) -> Tuple[bytes, str]:
#     """
#     Encodes the payload of an HTTP multipart response message.

#     Parameters
#     ----------
#     data: Sequence[bytes]
#         A sequence of byte data to include in the multipart message.
#     boundary: str, optional
#         The boundary string to separate parts of the message. If not provided, a unique boundary will be generated.

#     Returns
#     -------
#     Tuple[bytes, str]
#         The encoded HTTP request message body and the content type.
#     """
#     if not boundary:
#         boundary = binascii.hexlify(os.urandom(16)).decode()

#     content_type = f"multipart/related; type=application/dicom; boundary={boundary}"
#     body = b""

#     for payload in data:
#         body += f"\r\n--{boundary}\r\nContent-Type: application/dicom\r\n\r\n".encode(
#             "utf-8"
#         )
#         body += payload

#     body += f"\r\n--{boundary}--".encode("utf-8")

#     return body, content_type


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

        async def stream_study():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_study(), media_type="application/dicom")

    async def stream_multiple_series():
        first_boundary = None
        first_series = True
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

    return StreamingResponse(stream_multiple_series(), media_type="application/dicom")

    # boundary = None
    # encoded_files = []

    # for series_uid in mapped_series_uids:
    #     logging.info(f"Series: {series_uid}")

    #     dicom_file_response = await proxy_request(
    #         request, f"/studies/{study}/series/{series_uid}", "GET"
    #     )

    #     # Extract the boundary from the first part
    #     boundary = re.search(
    #         b"boundary=(.*)", dicom_file_response.headers["Content-Type"].encode()
    #     ).group(1)

    #     logging.info(f"Boundary: {boundary}")

    #     dicom_content = dicom_file_response.body

    #     # remove the boundary from the content
    #     dicom_content = dicom_content.replace(
    #         f"--{boundary.decode()}\r\n".encode(), b""
    #     ).replace(f"\r\n--{boundary.decode()}--".encode(), b"")

    #     encoded_files.append(dicom_content)

    # # debugpy.breakpoint()

    # body, content_type = _encode_multipart_message(encoded_files, boundary.decode())

    # return Response(content=body, media_type=content_type)


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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_series(), media_type="application/dicom")

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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_series(), media_type="application/dicom")

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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/frames/{frames}",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(
            stream_series(), media_type="application/dicom"
        )  # TODO: Check for Content-Location header

    else:

        return Response(status_code=204)


# TODO: Implement the bulk data retrieval
# @router.get("/{bulkdataReferenceURI}", tags=["WADO-RS"])
# async def retrieve_bulk_data(bulkdataReferenceURI: str, request: Request):
#     logging.info(f"bulkdataReferenceURI: {bulkdataReferenceURI}")
#     return await proxy_request(request, f"/{bulkdataReferenceURI}", "GET")


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
        return await proxy_request(request, f"/studies/{study}/metadata", "GET")

    all_metadata = []

    for series_uid in mapped_series_uids:
        metadata_response = await proxy_request(
            request, f"/studies/{study}/series/{series_uid}/metadata", "GET"
        )
        all_metadata.append(metadata_response.body)

    return Response(content=b"".join(all_metadata), media_type="application/dicom+json")


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
        return await proxy_request(
            request, f"/studies/{study}/series/{series}/metadata", "GET"
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
        return await proxy_request(
            request,
            f"/studies/{study}/series/{series}/instances/{instance}/metadata",
            "GET",
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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/rendered",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_series())

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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/rendered",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_series())

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

        async def stream_series():
            async with httpx.AsyncClient() as client:
                async with client.stream(
                    "GET",
                    f"{DICOMWEB_BASE_URL}/studies/{study}/series/{series}/instances/{instance}/rendered",
                    headers=dict(request.headers),
                ) as response:
                    async for chunk in response.aiter_bytes():
                        yield chunk

        return StreamingResponse(stream_series())

    else:
        return Response(status_code=204)
