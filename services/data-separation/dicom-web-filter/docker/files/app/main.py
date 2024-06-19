from fastapi import FastAPI, Request
from .QIDO_RS.routes import router as qido_router
from .STOW_RS.routes import router as stow_router
from .UPS_RS.routes import router as ups_router
from .WADO_RS.routes import router as wado_router
from .WADO_URI.routes import router as wado_uri_router
from .proxy_request import proxy_request
import logging

logger = logging.getLogger(__name__)

tags_metadata = [
    {
        "name": "QIDO-RS",
        "description": "Search for DICOM objects",
    },
    {
        "name": "WADO-RS",
        "description": "Retrieve DICOM objects",
    },
    {
        "name": "STOW-RS",
        "description": "Store DICOM objects",
    },
    {
        "name": "UPS-RS",
        "description": "Manage worklist items",
    },
    {
        "name": "Capabilities",
        "description": "Discover services",
    },
    {
        "name": "WADO-URI",
        "description": "Retrieve single DICOM instances",
    },
]

app = FastAPI(
    root_path="/dicom-web-filter",
    title="DICOM Web Filter",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
)

app.include_router(qido_router)
app.include_router(stow_router)
# app.include_router(ups_router) TODO: Test properly, currently no usecase
app.include_router(wado_router)
app.include_router(wado_uri_router, prefix="/wado-uri")


# TODO: Not working
@app.get("/", tags=["Capabilities"])
async def read_root(request: Request):
    return await proxy_request(request, "/", "GET")
