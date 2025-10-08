import logging
from fastapi import (
    Depends,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    Request,
)
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.logging_config import setup_logging
from app.api.v1.routers import workflow_runs, workflows
from app.dependencies import get_connection_manager
from app.database import async_engine
from app.models import Base
from app.api.v1.services import errors

setup_logging()
logger = logging.getLogger(__name__)

API_VERSION = "v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Kaapana Workflow API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.0.1",
    openapi_tags=[
        {
            "name": "workflow",
            "description": "Operations for workflow resources.",
        }
    ],
    lifespan=lifespan,
)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, con_mgr=Depends(get_connection_manager)
):
    await con_mgr.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        con_mgr.disconnect(websocket)


@app.exception_handler(errors.ServiceError)
async def service_exception_handler(request: Request, exc: errors.ServiceError):
    if isinstance(exc, errors.NotFoundError):
        status_code = 404
    elif isinstance(exc, errors.BadRequestError):
        status_code = 400
    elif isinstance(exc, errors.DependencyError):
        status_code = 503
    elif isinstance(exc, errors.InternalError):
        status_code = 500
    else:
        status_code = 500

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


# Versioned routers
app.include_router(
    workflow_runs.router, prefix=f"/{API_VERSION}", tags=["workflow runs"]
)
app.include_router(workflows.router, prefix=f"/{API_VERSION}", tags=["workflow"])
