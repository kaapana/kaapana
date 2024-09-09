from fastapi import FastAPI

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


# async def query_opensearch(series_uid: str):
#     """
#     Mock OpenSearch call. Replace this with actual OpenSearch querying logic.
#     Returns:
#     - 'local': for local processing
#     - 'remote': for remote processing
#     """
#     # Placeholder logic, return 'local' or 'remote' based on some condition.
#     if series_uid.startswith("1.2"):
#         return "local"
#     return "remote"


# @app.middleware("http")
# async def process_request_middleware(request: Request):
#     series_uid = request.query_params.get("SeriesUID", "default")
#     pacs = await query_opensearch(series_uid)

#     if pacs == "local":
#         return proxy_request(request, str(request.url), request.method, timeout=10)
#     elif pacs == "google":
#         print("Google Dcm Web")
#     else:
#         raise NotImplementedError(
#             "This will be implemented in the future. Currently supported PACS are: google, dcm4chee"
#         )
