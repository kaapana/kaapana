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
    Updates the query parameters with the `includefield` parameter, as required by DICOMweb APIs.

    This function is necessary for Google Cloud DICOM Store, as it does not return
    `StudyInstanceUID` and `SeriesInstanceUID` for instances by default.

    Args:
        query_params (dict): The original query parameters.
        includefield (str): The `includefield` parameter to add to the query.

    Returns:
        Dict: The updated query parameters with the `includefield` added.
    """
    query_params = dict(query_params)
    if not includefield:
        return query_params

    if "includefield" in query_params:
        query_params["includefield"] += "," + includefield
    else:
        query_params["includefield"] = includefield

    return query_params


async def stream(url: str, rs_endpoint: str, request_headers: dict, query_params: dict):
    """
    Streams data from a given URL while replacing metadata in the response.

    Args:
        url (str): The URL to stream data from.
        rs_endpoint (str): The resource endpoint URL.
        request_headers (dict): The headers to include in the request.
        query_params (dict): The query parameters to include in the request.

    Returns:
        StreamingResponse: A streaming response object with the streamed data.
    """
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
        return Response(
            status_code=204
        )  # Return 204 No Content if nothing was streamed.

    async def wrapped_stream():
        yield first_chunk  # Yield the first chunk first
        async for chunk in stream_generator:
            yield chunk

    return StreamingResponse(wrapped_stream(), media_type="application/dicom+json")


@router.get("/studies", tags=["QIDO-RS"])
async def query_studies(request: Request):
    """
    Queries all studies from the DICOMweb endpoint.

    Args:
        request (Request): The FastAPI request object containing query parameters and headers.

    Returns:
        StreamingResponse: A streaming response with the list of studies.
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
    """
    Queries all series within a given study from the DICOMweb endpoint.

    Args:
        study (str): The Study Instance UID.
        request (Request): The FastAPI request object containing query parameters and headers.

    Returns:
        StreamingResponse: A streaming response with the list of series within the study.
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
    """
    Queries all instances within a given series from the DICOMweb endpoint.

    Args:
        study (str): The Study Instance UID.
        series (str): The Series Instance UID.
        request (Request): The FastAPI request object containing query parameters and headers.

    Returns:
        StreamingResponse: A streaming response with the list of instances within the series.
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
