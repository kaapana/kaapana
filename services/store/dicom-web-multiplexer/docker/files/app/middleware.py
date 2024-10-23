import json
import re
import traceback

from app.crud import add_endpoint, get_endpoints, remove_endpoint
from app.database import get_session
from app.logger import get_logger
from app.proxy_request import proxy_request
from app.utils import dicom_web_filter_url
from fastapi import Request, Response
from fastapi.concurrency import iterate_in_threadpool
from fastapi.datastructures import URL
from fastapi.responses import StreamingResponse
from kaapanapy.helper.HelperOpensearch import HelperOpensearch
from starlette.middleware.base import BaseHTTPMiddleware

logger = get_logger(__name__)


class ProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Check if the request path starts with an excluded prefix
        if request.url.path.startswith("/dicom-web-multiplexer"):
            return await call_next(request)
        try:
            series_uid = get_series_uid_from_request(request)
            if series_uid:
                endpoint = get_endpoint_from_opensearch(series_uid)
                logger.info(f"Endpoint: {endpoint}")
                if endpoint:
                    request.state.endpoint = endpoint
                    return await call_next(request)

                return await proxy_request(
                    request=request,
                    url=dicom_web_filter_url(request),
                    method=request.method,
                )
            else:
                dicom_web_filter_result = await proxy_request(
                    request=request,
                    url=dicom_web_filter_url(request),
                    method=request.method,
                )

                dicom_web_multiplexer_result = await merge_external_responses(
                    request, call_next
                )

                return await decide_response(
                    dicom_web_filter_result, dicom_web_multiplexer_result
                )

        except Exception as e:
            logger.error(f"Error in proxy middleware: {e}")
            logger.error(traceback.format_exc())
            logger.error("Bad response from external PACS")
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
    query = {
        "bool": {"must": [{"term": {HelperOpensearch.series_uid_tag: series_uid}}]}
    }
    result = HelperOpensearch.get_query_dataset(
        index="project_1",
        query=query,
        include_custom_tag=HelperOpensearch.dcmweb_endpoint_tag,
    )
    try:
        endpoint = result[0]["_source"].get(HelperOpensearch.dcmweb_endpoint_tag)
        return endpoint
    except Exception:
        return None


async def merge_responses(response1: Response, response2: Response) -> Response:
    response1_media_type = response1.headers.get("content-type", "")
    response2_media_type = response2.headers.get("content-type", "")

    if response1.status_code != 200 or response2.status_code != 200:
        logger.info("One response is bad")
        return response1 if response1.status_code == 200 else response2

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
        logger.info("Merging json")
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
            media_type=response1_media_type,
            status_code=200,
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
    dicom_web_filter_result_type = dicom_web_filter_result.headers.get(
        "content-type", ""
    )
    dicom_web_multiplexer_result_type = dicom_web_multiplexer_result.headers.get(
        "content-type", ""
    )

    # Cannot merge binary responses as they have custom multipart/related boundary: hash, from dicom-web-filter
    # We always choose one that has returned successfully, favouring dicom_web_filter.
    if (
        dicom_web_filter_result.status_code == 200
        and "multipart/related" in dicom_web_filter_result_type
    ):
        logger.info("Binary dicom_web_filter_result")
        return dicom_web_filter_result
    # Same as above
    elif (
        dicom_web_multiplexer_result.status_code == 200
        and "multipart/related" in dicom_web_multiplexer_result_type
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


async def merge_external_responses(request: Request, call_next) -> Response | None:
    dicom_web_multiplexer_result = None

    async with get_session() as session:
        # List all endpoints (exactly one endpoint)
        endpoints = await get_endpoints(session)
        endpoint_strings = [ep.endpoint for ep in endpoints]
        logger.info(f"Endpoints {endpoint_strings}")

    for endpoint in endpoint_strings:
        request.state.endpoint = endpoint
        new_result = await call_next(request)

        if new_result.status_code == 200:
            logger.info(f"Processing endpoint: {endpoint}")
            dicom_web_multiplexer_result = (
                new_result
                if dicom_web_multiplexer_result is None
                else await merge_responses(new_result, dicom_web_multiplexer_result)
            )

    return dicom_web_multiplexer_result
