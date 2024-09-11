from fastapi import FastAPI, Request

from .config import DICOMWEB_BASE_URL
from .proxy_request import proxy_request

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


async def get_endpoint_from_opensearch(series_uid: str):
    return "local"


@app.middleware("http")
async def process_request_middleware(request: Request, call_next):
    series_uid = request.query_params.get("SeriesUID", "default")
    endpoint = await get_endpoint_from_opensearch(series_uid)

    if endpoint == "local":
        return await proxy_request(
            request, str(request.url), request.method, timeout=10
        )
    else:
        response = await call_next(request)
        return response
