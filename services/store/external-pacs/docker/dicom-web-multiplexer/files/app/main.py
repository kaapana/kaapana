import logging

from app.middleware import ProxyMiddleware
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager

from .database import async_engine
from .MANAGEMENT.routes import router as management_router
from .models import Base
from .QIDO_RS.routes import router as qido_router
from .SUPPLEMENTS.routes import router as supplement_router
from .WADO_RS.routes import router as wado_router

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
        "name": "SUPPLEMENTS",
        "description": "Supplement routes - Thumbnail",
    },
    {
        "name": "MANAGEMENT",
        "description": "Management routes, add, retrieve or delete external endpoints",
    },
]

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield  # This yield separates startup from shutdown code
    # Code here would run after the application stops


app = FastAPI(
    title="DICOM Web Multiplexer",
    docs_url="/dicom-web-filter/management/docs",
    openapi_url="/dicom-web-filter/management/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)
app.add_middleware(ProxyMiddleware)
app.include_router(qido_router, prefix="/dicom-web-filter")
app.include_router(supplement_router, prefix="/dicom-web-filter")
app.include_router(wado_router, prefix="/dicom-web-filter")
app.include_router(management_router, prefix="/dicom-web-filter/management")
