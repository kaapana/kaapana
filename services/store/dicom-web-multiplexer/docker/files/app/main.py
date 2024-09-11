from fastapi import FastAPI, Request

from .proxy_request import proxy_request

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


@app.middleware("http")
async def process_request_middleware(request: Request, call_next):
    return await proxy_request(request, str(request.url), request.method, timeout=10)
