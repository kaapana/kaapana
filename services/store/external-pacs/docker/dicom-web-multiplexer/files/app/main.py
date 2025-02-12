import logging

from fastapi.middleware import Middleware

from app.middleware import ProxyMiddleware
from app.auth_middleware import AuthMiddleware
from fastapi import FastAPI

from .config import DWF_IDENTITY_OPENID_CLIENT_ID, DWF_IDENTITY_OPENID_CONFIG_URL
from .QIDO_RS.routes import router as qido_router
from .WADO_RS.routes import router as wado_router
from .SUPPLEMENTS.routes import router as supplement_router
from .STOW_RS.routes import router as stow_router
from .CUSTOM.routes import router as custom_router
from .MANAGEMENT.routes import router as management_router

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
        "name": "MULTIPLEXER",
        "description": "Management routes, add, retrieve or delete external endpoints",
    },
]

logger = logging.getLogger(__name__)



app = FastAPI(
    title="DICOM Web Multiplexer",
    docs_url="/management/docs",
    openapi_url="/management/openapi.json",
    version="0.1.0",
    openapi_tags=tags_metadata,
    middleware=[
        Middleware(
            AuthMiddleware,
            config_url=DWF_IDENTITY_OPENID_CONFIG_URL,
            client_id=DWF_IDENTITY_OPENID_CLIENT_ID,
        ),
        Middleware(ProxyMiddleware),
    ],
)
app.include_router(qido_router)
app.include_router(wado_router)
app.include_router(supplement_router)
app.include_router(custom_router)
app.include_router(stow_router, prefix="/external")
app.include_router(management_router, prefix="/management")
