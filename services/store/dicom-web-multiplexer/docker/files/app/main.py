from fastapi import FastAPI, Request, Response

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
    # openapi_tags=tags_metadata,
)


async def query_opensearch(series_uid: str):
    """
    Mock OpenSearch call. Replace this with actual OpenSearch querying logic.
    Returns:
    - 'local': for local processing
    - 'remote': for remote processing
    """
    # Placeholder logic, return 'local' or 'remote' based on some condition.
    if series_uid.startswith("1.2"):
        return "local"
    return "remote"


@app.middleware("http")
async def process_request_middleware(request: Request, call_next):
    # Extract the seriesUID or any other parameter you need to make the decision
    series_uid = request.query_params.get("SeriesUID", "default")

    # Call OpenSearch to decide where to process the request
    decision = await query_opensearch(series_uid)

    if decision == "local":
        # Redirect to the local PACS (e.g., your DICOM Web Filter)
        local_pacs_url = "http://localhost:8042/dicom-web" + request.url.path

        # Reconstruct the original query parameters
        if request.query_params:
            local_pacs_url += f"?{request.query_params}"

        # Use httpx to make an asynchronous request to the local PACS
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=request.method,
                url=local_pacs_url,
                headers=dict(request.headers),
                data=await request.body(),
            )

        # Return the local PACS response
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )

    # If it's a remote request, let FastAPI handle it
    response = await call_next(request)
    return response
