from app.middleware import ProxyMiddleware
from fastapi import FastAPI

from .QIDO_RS.routes import router as qido_router
from .SUPPLEMENTS.routes import router as supplement_router
from .WADO_RS.routes import router as wado_router

app = FastAPI(
    root_path="/dicom-web-filter",
    title="DICOM Web Multiplexer",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)

app.include_router(qido_router)
app.include_router(supplement_router)
app.include_router(wado_router)
app.add_middleware(ProxyMiddleware)
