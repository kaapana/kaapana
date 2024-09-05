import logging

import httpx
from fastapi import Request, Response

from .config import DICOMWEB_BASE_URL

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.WARNING)  # TODO: Change before deployment


async def proxy_request(
    request: Request, path: str, method: str, base_url=DICOMWEB_BASE_URL, timeout=10
):
    url = f"{base_url}{path}"
    headers = dict(request.headers)
    # logger.info(f"Request URL: {url}")
    # logger.info(f"Request headers: {headers}")
    # logger.info(f"Request method: {method}")

    async with httpx.AsyncClient() as client:

        client.timeout = timeout  # Set timeout for the client

        if method == "GET":
            logging.info(f"Query params: {request.query_params}")
            response = await client.get(
                url, headers=headers, params=request.query_params
            )
        elif method == "POST":
            body = await request.body()
            response = await client.post(url, headers=headers, content=body)
        elif method == "OPTIONS":
            response = await client.options(url, headers=headers)
        elif method == "PUT":
            body = await request.body()
            response = await client.put(url, headers=headers, content=body)
        elif method == "DELETE":
            response = await client.delete(url, headers=headers)
        else:
            return Response(status_code=405)

    # logger.info(f"Response status code: {response.status_code}")
    # logger.info(f"Response headers: {response.headers}")
    # logger.info(f"Response content: {response.content[:100]}")
    # logger.info(f"Response encoding: {response.encoding}")
    # logger.info(f"Response text: {response.text[:100]}")

    # Store raw values
    status_code = response.status_code
    response_headers = dict(response.headers)
    content = response.content

    # Prepare response headers
    if "content-encoding" in response_headers:
        del response_headers["content-encoding"]
    if "content-length" in response_headers:
        del response_headers["content-length"]  # Let the server set the content length

    # Construct a new Response object from stored values
    return Response(
        content=content,
        status_code=status_code,
        headers=response_headers,
        media_type=response_headers.get("content-type"),
    )
