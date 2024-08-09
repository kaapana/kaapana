from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from .models import Base
from .database import async_engine
from .QIDO_RS.routes import router as qido_router
from .STOW_RS.routes import router as stow_router
from .WADO_RS.routes import router as wado_router
from .CUSTOM_RS.routes import router as custom_router
from .WADO_URI.routes import router as wado_uri_router
from .proxy_request import proxy_request
import logging

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # This yield separates startup from shutdown code
    # Code here would run after the application stops


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
    {
        "name": "Custom",
        "description": "Custom routes, currently for dcm4chee delete endpoint",
    },
]

app = FastAPI(
    root_path="/dicom-web-filter",
    title="DICOM Web Filter",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)

app.include_router(qido_router)
app.include_router(stow_router)
app.include_router(wado_router)
app.include_router(custom_router)
app.include_router(wado_uri_router, prefix="/wado-uri")


# TODO: Not working
@app.get("/", tags=["Capabilities"])
async def read_root(request: Request):
    return await proxy_request(request, "/", "GET")
