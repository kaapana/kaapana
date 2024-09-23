import logging
import sys
from fastapi import FastAPI, Request
from .proxy_request import proxy_request
from .config import DICOMWEB_BASE_URL

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)

import debugpy
debugpy.listen(("localhost", 17777))
debugpy.wait_for_client()
debugpy.breakpoint()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
stream_handler = logging.StreamHandler(sys.stdout)
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')
stream_handler.setFormatter(log_formatter)
logger.addHandler(stream_handler)

async def get_endpoint_from_opensearch(series_uid: str):
    return "local"

@app.middleware("https")
async def process_request_middleware(request: Request, call_next):
    logger.info("Proxy request middleware")
    logger.info(request)
    series_uid = request.query_params.get("SeriesUID", "default")
    endpoint = await get_endpoint_from_opensearch(series_uid)
    
    if endpoint == "local":
        logger.info("Local: Redirect to dicom-web-filter")
        return await proxy_request(
            request, str(request.url), request.method, timeout=10
        )
    else:
        response = await call_next(request)
        return response
    
@app.middleware("http")
async def process_request_middleware(request: Request, call_next):
    logger.info("Proxy request middleware")
    logger.info(request)
    # endpoint = await get_endpoint_from_opensearch(series_uid)
    
    
    logger.info("Local: Redirect to dicom-web-filter")
    return await proxy_request(
        request, str(request.url), request.method, timeout=10
    )