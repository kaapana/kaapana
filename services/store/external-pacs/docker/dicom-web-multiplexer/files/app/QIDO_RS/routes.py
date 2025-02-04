from typing import Dict


from app.auth import authorize_headers
from app.logger import get_logger
from app.streaming_helpers import metadata_replace_stream
from app.utils import rs_endpoint_url
from fastapi import APIRouter, Request, Response
from fastapi.responses import StreamingResponse

router = APIRouter()
logger = get_logger(__file__)


def update_query_params(query_params: dict, includefield: str = "") -> Dict:
    """
    Update query params with includefield, as DICOMWeb API.
    Neccessary for Gcloud Dicom Store, as it does not return
    StudyUID and SeriesUID for instances by default.
    """
    query_params = dict(query_params)
    if not includefield:
        return query_params

    if "includefield" in query_params:
        query_params["includefield"] += "," + includefield
    else:
        query_params["includefield"] = includefield

    return query_params


async def stream(url, rs_endpoint, request_headers, query_params):
    stream_generator = metadata_replace_stream(
        method="GET",
        url=url,
        search="/".join(rs_endpoint.split(":")[-1].split("/")[1:]).encode(),
        replace=b"dicom-web-filter",
        headers=request_headers,
        query_params=query_params,
    )

    first_chunk = None
    async for chunk in stream_generator:
        first_chunk = chunk
        break  # We only check the first chunk, then continue normally.

    if first_chunk is None:
        return Response(status_code=204)  # Return 204 No Content if nothing was streamed.

    async def wrapped_stream():
        yield first_chunk  # Yield the first chunk first
        async for chunk in stream_generator:
            yield chunk

    return StreamingResponse(wrapped_stream(), media_type="application/dicom+json")


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    """This endpoint is used to get all series of a study.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: StreamingResponse object
    """
    rs_endpoint = rs_endpoint_url(request)
    auth_headers = await authorize_headers(request)
    includefield = "StudyInstanceUID"
    query_params = update_query_params(request.query_params, includefield=includefield)

    return await stream(
        url=f"{rs_endpoint}/studies",
        rs_endpoint=rs_endpoint,
        request_headers=auth_headers,
        query_params=query_params,
    )


@router.get("/studies/{study}/series", tags=["QIDO-RS"])
async def query_series(study: str, request: Request):
    """This endpoint is used to get all series of a study.

    Args:
        study (str): Study Instance UID
        request (Request): Request object

    Returns:
        response: StreamingResponse object
    """

    rs_endpoint = rs_endpoint_url(request)
    auth_headers = await authorize_headers(request)
    includefield = "StudyInstanceUID"
    query_params = update_query_params(request.query_params, includefield=includefield)

    return await stream(
        url=f"{rs_endpoint}/studies/{study}/series",
        rs_endpoint=rs_endpoint,
        request_headers=auth_headers,
        query_params=query_params,
    )


@router.get("/studies/{study}/series/{series}/instances", tags=["QIDO-RS"])
async def query_instances(
    study: str,
    series: str,
    request: Request,
):
    """This endpoint is used to get all instances of a series.

    Args:
        study (str): Study Instance UID
        series (str): Series Instance UID
        request (Request): Request object

    Returns:
        response: StreamingResponse object
    """
    rs_endpoint = rs_endpoint_url(request)
    auth_headers = await authorize_headers(request)

    includefield = "StudyInstanceUID,SeriesInstanceUID,Modality"
    query_params = update_query_params(request.query_params, includefield=includefield)

    return await stream(
        url=f"{rs_endpoint}/studies/{study}/series/{series}/instances",
        rs_endpoint=rs_endpoint,
        request_headers=auth_headers,
        query_params=query_params,
    )
