from fastapi import FastAPI, Request

from .proxy_request import proxy_request

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


async def get_endpoint_from_opensearch(series_uid: str):
    """
    Mock OpenSearch call. Replace this with actual OpenSearch querying logic.
    Returns:
    - 'local': for local processing
    - 'remote': for remote processing
    """
    # Placeholder logic, return 'local' or 'remote' based on some condition.
    return "Local"


@app.middleware("http")
async def process_request_middleware(request: Request):

    series_uid = request.query_params.get("SeriesUID", "default")
    endpoint = await get_endpoint_from_opensearch(series_uid)

    if endpoint == "local":
        return proxy_request(request, str(request.url), request.method, timeout=10)
    elif endpoint == "google":
        print("Google Dcm Web")
    else:
        raise NotImplementedError(
            "This will be implemented in the future. Currently supported PACS are: google, dcm4chee"
        )
