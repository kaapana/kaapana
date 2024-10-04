import logging
import sys


from fastapi import Request, Response
from fastapi.datastructures import URL
from starlette.middleware.base import BaseHTTPMiddleware
import httpx
from app.config import DICOMWEB_BASE_URL

from app.main import app

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
)
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)
logging.basicConfig(level=logging.DEBUG)


class ProxyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger.info("Entering ProxyMiddleware")
        
        new_url = DICOMWEB_BASE_URL + str(request.url).split('dicom-web-filter')[-1]

        return await proxy_request(
            request=request,
            url=new_url,
            method=request.method,
        )


# Add the middleware to the FastAPI app
app.add_middleware(ProxyMiddleware)


async def proxy_request(
    request: Request, url: str, method: str, query_params: dict | None = None, timeout=10
):
    headers = dict(request.headers)
    logger.info(f"Request URL: {url}")
    logger.info(f"Request headers: {headers}")
    logger.info(f"Request method: {method}")

    async with httpx.AsyncClient() as client:
        client.timeout = timeout  # Set timeout for the client

        if method == "GET":
            if query_params is None:
                query_params = request.query_params
            logging.info(f"Query params: {query_params}")
            response = await client.get(url, headers=headers, params=query_params)
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

    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response headers: {response.headers}")
    logger.info(f"Response content: {response.content[:100]}")
    logger.info(f"Response encoding: {response.encoding}")
    logger.info(f"Response text: {response.text[:100]}")

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
