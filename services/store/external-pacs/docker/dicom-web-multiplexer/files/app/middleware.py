import json
import re
from typing import List


from app.logger import get_logger
from app.proxy_request import proxy_request
from app.utils import dicom_web_filter_url

from fastapi import Request, Response
from fastapi.concurrency import iterate_in_threadpool
from fastapi.datastructures import URL
from fastapi.responses import StreamingResponse
from kaapanapy.helper.HelperOpensearch import DicomTags, HelperOpensearch
from kaapanapy.helper import get_opensearch_client
from starlette.middleware.base import BaseHTTPMiddleware

import logging

logger = get_logger(__name__, level=logging.DEBUG)


class ProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        """
        Intercepts incoming requests, routes them based on custom rules,
        and proxies requests to the appropriate DICOM server or external PACS.

        Args:
            request (Request): The incoming FastAPI request.
            call_next (callable): The next middleware or route handler.

        Returns:
            Response: The HTTP response after handling the request.
        """
        # Triggered by LocalExternalPACSOperator on first import of external PACS (So it does not include any local dicom-web-filter results.)
        if "X-Endpoint-URL" in request.headers:
            request.state.endpoint = request.headers["X-Endpoint-URL"]
            return await call_next(request)

        # Multiplexer - CRUD External Pacs
        if "management" in request.url.path:
            return await call_next(request)

        # docs or dicom-web-filter project paths ("projects" is also used by delete so we use "data")
        if "docs" in request.url.path or "data" in request.url.path:
            return await proxy_dicom_web_filter(request=request)

        # Determine endpoint based on Series UID or proxy request to DICOM Web Filter
        series_uid = get_series_uid_from_request(request)
        access_token = request.headers["x-forwarded-access-token"]

        if series_uid:
            logger.debug(f"Request has series_uid: {series_uid}")
            endpoint = get_endpoint_from_opensearch(series_uid, access_token)

            if endpoint:
                logger.debug(f"Data Source endpoint: {endpoint}")
                request.state.endpoint = endpoint
                return await call_next(request)

            logger.debug(
                f"No data source endpoint found in OpenSearch, request dicom-web-filter"
            )
            return await proxy_dicom_web_filter(request=request)
        else:
            logger.debug(
                "No Series UID -> requests all PACS found in meta, merging external and local PACS responses"
            )
            endpoints = get_unique_dcmweb_endpoints(access_token=access_token)
            logger.debug(f"Found endpoints: {endpoints}")

            dicom_web_filter_result = await proxy_dicom_web_filter(request=request)
            dicom_web_multiplexer_result = await dicom_web_multiplexer_responses(
                endpoints, request, call_next
            )
            return await decide_response(
                dicom_web_filter_result, dicom_web_multiplexer_result
            )


def get_study_uid_from_request(request: URL) -> str | None:
    """
    Extracts the Study UID from the request URL if present.

    Args:
        request (URL): The FastAPI request URL object.

    Returns:
        Optional[str]: The extracted Study UID, or None if not found.
    """
    match = re.search(r"/study/([0-9.]+)", str(request.url))
    return match.group(1) if match else None


def get_series_uid_from_request(request: URL) -> str | None:
    """
    Extracts the Series UID from the request URL if present.

    Args:
        request (URL): The FastAPI request URL object.

    Returns:
        Optional[str]: The extracted Series UID, or None if not found.
    """
    match = re.search(r"/series/([0-9.]+)", str(request.url))
    return match.group(1) if match else None


def get_endpoint_from_opensearch(series_uid: str, access_token: str) -> str:
    """
    Queries OpenSearch to find the DICOM Web endpoint for a given Series UID.

    Args:
        series_uid (str): The Series UID to search for.
        access_token (str): The access token for authentication.

    Returns:
        Optional[str]: The DICOM Web endpoint if found, else None.
    """
    query = {"bool": {"must": [{"term": {DicomTags.series_uid_tag: series_uid}}]}}
    os_helper = HelperOpensearch(access_token=access_token)
    # No index specified, querying across all accessible indices
    result = os_helper.get_query_dataset(
        query=query,
        include_custom_tag=DicomTags.dcmweb_endpoint_tag,
    )
    if not result:
        return None
    return result[0]["_source"].get(DicomTags.dcmweb_endpoint_tag)


def get_unique_dcmweb_endpoints(access_token: str) -> List[str]:
    os_client = get_opensearch_client(access_token=access_token)
    # Define the aggregation query for unique DICOMweb endpoints

    query = {
        "size": 0,  # No document hits, only aggregations
        "aggs": {
            "unique_dcmweb_endpoints": {
                "terms": {
                    "field": f"{DicomTags.dcmweb_endpoint_tag}.keyword",  # Aggregate on the endpoint tag
                    "size": 100,  # Increase this size if expecting more unique endpoints
                }
            }
        },
    }

    try:
        # No index specified, querying across all accessible indices
        response = os_client.search(body=query)
        # Extract unique DICOMweb endpoints from the aggregation results
        unique_endpoints = [
            bucket["key"]
            for bucket in response["aggregations"]["unique_dcmweb_endpoints"]["buckets"]
        ]
        return unique_endpoints
    except Exception as e:
        logger.error(f"Error retrieving unique DICOMweb endpoints: {e}")
        raise e


async def merge_responses(
    response1: Response | None, response2: Response | None
) -> Response:
    """
    Merges two responses if they have the same JSON-compatible content type,
    preferring non-failing responses. If merging is unsupported or impossible,
    an appropriate error response is returned.

    Args:
        response1 (Optional[Response]): The primary response to be merged.
        response2 (Optional[Response]): The secondary response to be merged.

    Returns:
        Response: Merged JSON response or an error if merging is not feasible.
    """

    if not response1 or response1.status_code != 200:
        logger.warning(f"Response from: {response1} failed")
        return response2

    if not response2 or response2.status_code != 200:
        logger.warning(f"Response from: {response2} failed")
        return response1

    response1_media_type = response1.headers.get("content-type", "")
    response2_media_type = response2.headers.get("content-type", "")
    if response1_media_type != response2_media_type:
        logger.error(
            f"Cannot merge responses with different media types: {response1_media_type} vs {response2_media_type}"
        )
        return Response(
            content="Cannot merge responses with different media types",
            status_code=400,
            media_type="text/plain",
        )

    if response1_media_type in ["application/json", "application/dicom+json"]:
        response1_data = await get_json_response_body(response1)
        response2_data = await get_json_response_body(response2)

        # TODO: Dicom Web Filter return 200 and {'errorMessage': 'No matches found.'} with studies/{study}/metadata
        if isinstance(response1_data, list) and isinstance(response2_data, list):
            merged_content = response1_data + response2_data  # Concatenate lists

        elif isinstance(response1_data, list):
            merged_content = response1_data

        elif isinstance(response2_data, list):
            merged_content = response2_data

        else:
            return Response(
                content="Unable to merge request from external and local pacs",
                status_code=500,
            )

        return Response(
            content=json.dumps(merged_content),
            status_code=200,
            media_type=response1_media_type,
        )

    if not response1_media_type and not response2_media_type:
        return Response(status_code=200)

    return Response(
        content=f"Unsupported media type for merging {response1_media_type}",
        status_code=415,
        media_type="text/plain",
    )


async def get_json_response_body(response: Response) -> dict:
    """
    Extracts the JSON body from a Response object.

    Args:
        response (Response): The response to extract the JSON body from.

    Returns:
        Union[dict, list]: The extracted JSON data.
    """
    if isinstance(response, StreamingResponse):
        body_parts = [section async for section in response.body_iterator]
        response.body_iterator = iterate_in_threadpool(iter(body_parts))
        body = b"".join(body_parts).decode("utf-8")
    else:
        body = response.body.decode("utf-8") if response.body else ""

    return json.loads(body) if body else []


async def decide_response(
    dicom_web_filter_result: Response, dicom_web_multiplexer_result: Response | None
) -> Response:
    """
    Determines the appropriate response based on the filter and multiplexer results.

    Args:
        dicom_web_filter_result (Response): The result from the DICOM Web filter request.
        dicom_web_multiplexer_result (Optional[Response]): The result from the multiplexer request.

    Returns:
        Response: The chosen or merged response.
    """
    # Cannot merge binary responses as they have custom multipart/related boundary: hash, from dicom-web-filter
    # We always choose one that has returned successfully, favouring dicom_web_filter.

    if not dicom_web_multiplexer_result:
        logger.debug("No external result, returning dicom-web-filter results")
        return dicom_web_filter_result

    if (
        dicom_web_filter_result.status_code == 200
        and "multipart/related"
        in dicom_web_filter_result.headers.get("content-type", "")
    ):
        logger.debug("Binary dicom_web_filter result")
        return dicom_web_filter_result

    elif (
        dicom_web_multiplexer_result.status_code == 200
        and "multipart/related"
        in dicom_web_multiplexer_result.headers.get("content-type", "")
    ):
        logger.debug("Binary dicom_web_multiplexer_result")
        return dicom_web_filter_result

    elif (
        dicom_web_multiplexer_result.status_code == 200
        and dicom_web_filter_result.status_code == 200
    ):
        logger.debug("Merging multiplexer and dicom-web-filter response")
        return await merge_responses(
            dicom_web_filter_result, dicom_web_multiplexer_result
        )

    else:
        return dicom_web_filter_result


async def proxy_dicom_web_filter(request: Request) -> Response:
    """
    Proxies a request to the DICOM Web filter.

    Args:
        request (Request): The incoming FastAPI request.

    Returns:
        Response: The response from the DICOM Web filter.
    """

    return await proxy_request(
        request=request,
        url=dicom_web_filter_url(request),
        method=request.method,
    )


async def dicom_web_multiplexer_responses(
    endpoints: List[str], request: Request, call_next: callable
) -> Response | None:
    """
    Aggregates responses from multiple external PACS endpoints.

    Args:
        endpoints (List[str]): A list of DICOM Web endpoint URLs to query for data.
        request (Request): The incoming request, typically a DICOM web request.
        call_next (Callable): A function that passes the request to the next middleware
                               or route handler and returns the response.

    Returns:
        Optional[Response]: The merged response if at least one endpoint responds successfully,
                             or None if no successful responses are received.
    """
    
    merged_result = None
    for endpoint in endpoints:
        request.state.endpoint = endpoint
        result = await call_next(request)

        if result.status_code == 200:
            merged_result = (
                result
                if not merged_result
                else await merge_responses(result, merged_result)
            )

    return merged_result
