import json
import re
import traceback

from app.crud import get_endpoints
from app.database import get_session
from app.logger import get_logger
from app.proxy_request import proxy_request
from app.utils import dicom_web_filter_url
from fastapi import Request, Response
from fastapi.concurrency import iterate_in_threadpool
from fastapi.datastructures import URL
from fastapi.responses import StreamingResponse
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from kaapanapy.settings import OpensearchSettings
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)

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
        
        # Triggered by LocalExternalPACSOperator on first import of external dags (So it does not include any local dicom-web-filter results.)
        if "X-Endpoint-URL" in request.headers:
            request.state.endpoint = request.headers["X-Endpoint-URL"]
            return await call_next(request)
        
        # Specific routes meant for multiplexer management should skip dicom-web-filter
        if request.url.path.startswith("/dicom-web-multiplexer"):
            return await call_next(request)
        
        try:
            # Determine endpoint based on Series UID or proxy request to DICOM Web Filter
            series_uid = get_series_uid_from_request(request)
            logger.info("Request has series_uid")
            if series_uid:                
                endpoint = get_endpoint_from_opensearch(series_uid)
                if endpoint:
                    logger.info(f"Opensearch endpoint: {endpoint}")
                    request.state.endpoint = endpoint
                    return await call_next(request)

                # No endpoint found in OpenSearch, fall back to dicom-web-filter request
                return await proxy_dicom_web_filter(request=request)
            else:
                 # No Series UID: process requests for all PACS, merging external and local PACS responses
                dicom_web_filter_result = await proxy_dicom_web_filter(request=request)
                dicom_web_multiplexer_result = await get_external_responses(request, call_next)

                logger.info("Merge External PACS responses with Local Dicom Web Filter")
                return await decide_response(
                    dicom_web_filter_result, dicom_web_multiplexer_result
                )

        except Exception as e:
            logger.error(f"Error in proxy middleware: {e}")
            logger.error(traceback.format_exc())
            logger.error(request.url)
            return Response(
                content="Error in proxy middleware",
                status_code=400,
                media_type="text/plain",
            )


def get_study_uid_from_request(request: URL) -> str | None:
    url = str(request.url)
    pattern = r"/study/([0-9.]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_series_uid_from_request(request: URL) -> str | None:
    url = str(request.url)
    pattern = r"/series/([0-9.]+)"
    match = re.search(pattern, url)
    return match.group(1) if match else None


def get_endpoint_from_opensearch(series_uid: str) -> str:
    index = OpensearchSettings().default_index
    query = {
        "bool": {"must": [{"term": {HelperOpensearch.series_uid_tag: series_uid}}]}
    }
    result = HelperOpensearch.get_query_dataset(
        index=index,
        query=query,
        include_custom_tag=HelperOpensearch.dcmweb_endpoint_tag,
    )
    try:
        endpoint = result[0]["_source"].get(HelperOpensearch.dcmweb_endpoint_tag)
        return endpoint
    except Exception:
        return None


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
        logger.info("Merging 2 JSON responses.")

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

    return Response(
        content=f"Unsupported media type for merging {response1_media_type}",
        status_code=415,
        media_type="text/plain",
    )


async def get_json_response_body(response: Response) -> dict:
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
    Determines the response to return based on the success and content type of the DICOM web filter 
    and multiplexer results. Favors dicom_web_filter_result when both responses are available and unmergeable.

    Args:
        dicom_web_filter_result (Response): The result from the dicom-web-filter request.
        dicom_web_multiplexer_result (Optional[Response]): The result from the external PACS multiplexer request.

    Returns:
        Response: The chosen/merged response, based on content type and success status.
    """
    
    # Cannot merge binary responses as they have custom multipart/related boundary: hash, from dicom-web-filter
    # We always choose one that has returned successfully, favouring dicom_web_filter.
    if not dicom_web_multiplexer_result:
        logger.info("No external result, returning dicom-web-filter results")
        return dicom_web_filter_result

    if (
        dicom_web_filter_result.status_code == 200
        and "multipart/related"
        in dicom_web_filter_result.headers.get("content-type", "")
    ):
        logger.info("Binary dicom_web_filter result")
        return dicom_web_filter_result

    elif (
        dicom_web_multiplexer_result.status_code == 200
        and "multipart/related"
        in dicom_web_multiplexer_result.headers.get("content-type", "")
    ):
        logger.info("Binary dicom_web_multiplexer_result")
        return dicom_web_filter_result

    # If the responses are not multipart/related we can merge (json, text)
    elif (
        dicom_web_multiplexer_result.status_code == 200
        and dicom_web_filter_result.status_code == 200
    ):
        logger.info("Merging multiplexer and dicom-web-filter response")
        return await merge_responses(
            dicom_web_filter_result, dicom_web_multiplexer_result
        )

    else:
        return dicom_web_filter_result




async def proxy_dicom_web_filter(request: Request) -> Response:
    """Proxies request to DICOM Web Filter."""
    return await proxy_request(
        request=request,
        url=dicom_web_filter_url(request),
        method=request.method,
    )
    
async def get_external_responses(request: Request, call_next: callable) -> Response | None:
    """
    Aggregates responses from external PACS endpoints and returns a merged result.

    Args:
        request (Request): The incoming request.
        call_next (callable): The next middleware or route handler.

    Returns:
        Response | None: Merged response from all external endpoints, or None if no endpoints respond successfully.
    """
    async with get_session() as session:
        endpoints = await get_endpoints(session)
    endpoint_strings = [ep.endpoint for ep in endpoints]
    logger.info(f"Found endpoints: {endpoint_strings}")

    dicom_web_multiplexer_result = None
    for endpoint in endpoint_strings:
        request.state.endpoint = endpoint
        new_result = await call_next(request)

        if new_result.status_code == 200:
            logger.info(f"Processing endpoint: {endpoint}")
            dicom_web_multiplexer_result = (
                new_result if dicom_web_multiplexer_result is None
                else await merge_responses(new_result, dicom_web_multiplexer_result)
            )

    return dicom_web_multiplexer_result