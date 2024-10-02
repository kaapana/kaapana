from fastapi import FastAPI

app = FastAPI(
    root_path="/dicom-web-multiplexer",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)

from app.middleware import ProxyMiddleware

app.add_middleware(ProxyMiddleware)
