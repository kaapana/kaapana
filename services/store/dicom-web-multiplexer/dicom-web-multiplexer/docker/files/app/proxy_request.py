import httpx
from app.logger import get_logger
from fastapi import Request, Response
from starlette.responses import StreamingResponse

logger = get_logger(__name__)


async def proxy_request(
    request: Request,
    url: str,
    method: str,
    timeout=10,
):
    headers = dict(request.headers)
    logger.info(f"Request URL: {url}")
    logger.debug(f"Request headers: {headers}")
    logger.debug(f"Request method: {method}")

    async with httpx.AsyncClient() as client:
        client.timeout = timeout  # Set timeout for the client

        if method == "GET":
            response = await client.get(url, headers=headers)
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

    logger.debug(f"Response status code: {response.status_code}")
    logger.debug(f"Response headers: {response.headers}")
    logger.debug(f"Response content: {response.content[:100]}")
    logger.debug(f"Response encoding: {response.encoding}")
    logger.debug(f"Response text: {response.text[:100]}")

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


async def stream_proxy_request(
    request: Request,
    url: str,
    method: str,
    timeout=10,
):
    headers = dict(request.headers)
    logger.info(f"Request URL: {url}")
    logger.debug(f"Request headers: {headers}")
    logger.debug(f"Request method: {method}")

    async with httpx.AsyncClient(timeout=timeout) as client:
        if method == "GET":
            response = await client.stream("GET", url, headers=headers)
        elif method == "POST":
            body = await request.body()
            response = await client.stream("POST", url, headers=headers, content=body)
        elif method == "OPTIONS":
            response = await client.stream("OPTIONS", url, headers=headers)
        elif method == "PUT":
            body = await request.body()
            response = await client.stream("PUT", url, headers=headers, content=body)
        elif method == "DELETE":
            response = await client.stream("DELETE", url, headers=headers)
        else:
            return Response(status_code=405)

    # Function to iterate and stream the response content
    async def stream_response():
        async for chunk in response.aiter_bytes():
            yield chunk

    # Remove certain headers that should not be forwarded
    response_headers = dict(response.headers)
    if "content-encoding" in response_headers:
        del response_headers["content-encoding"]
    if "content-length" in response_headers:
        del response_headers["content-length"]

    # Return a StreamingResponse
    return StreamingResponse(
        stream_response(),
        status_code=response.status_code,
        headers=response_headers,
        media_type=response_headers.get("content-type"),
    )
