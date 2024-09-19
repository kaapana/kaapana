import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware import Middleware

from .auth_middleware import AuthMiddleware
from .config import DWF_IDENTITY_OPENID_CLIENT_ID, DWF_IDENTITY_OPENID_CONFIG_URL
from .CUSTOM_RS.routes import router as custom_router
from .database import async_engine
from .models import Base
from .DATAPROJECTS.routes import router as dataprojects_router
from .QIDO_RS.routes import router as qido_router
from .STOW_RS.routes import router as stow_router
from .SUPPLEMENTS.routes import router as supplements_router
from .WADO_RS.routes import router as wado_router
from .WADO_URI.routes import router as wado_uri_router


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
    {
        "name": "DataProjects",
        "description": "Filter specific routes, create and delete DataProject mappings",
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
    middleware=[
        Middleware(
            AuthMiddleware,
            config_url=DWF_IDENTITY_OPENID_CONFIG_URL,
            client_id=DWF_IDENTITY_OPENID_CLIENT_ID,
        )
    ],
)

app.include_router(qido_router)
app.include_router(stow_router)
app.include_router(wado_router)
app.include_router(custom_router)
app.include_router(supplements_router)
app.include_router(dataprojects_router)
app.include_router(wado_uri_router, prefix="/wado-uri")
