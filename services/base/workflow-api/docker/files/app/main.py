import asyncio
import logging
import os
from contextlib import asynccontextmanager

from app.api.v1.routers import (
    dummy_adapter_status,
    health_check,
    workflow_runs,
    workflows,
)
from app.api.v1.services import errors
from app.dependencies import get_connection_manager
from app.logging_config import setup_logging
from app.sync import run_sync
from fastapi import Depends, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

setup_logging()
logger = logging.getLogger(__name__)

API_VERSION = "v1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run sync in the background without blocking the API
    sync_task = asyncio.create_task(run_sync(interval_seconds=30))
    yield
    # Shutdown: Cancel the sync task
    sync_task.cancel()
    try:
        await sync_task
    except asyncio.CancelledError:
        pass


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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow all frontend origins in dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
app.include_router(health_check.router, prefix=f"/{API_VERSION}", tags=["health"])

logger.info('test {os.getenv("ENABLE_TEST_ADAPTER", "false")}')
if os.getenv("ENABLE_TEST_ADAPTER", "false").lower() == "true":
    logger.info("Enabling DummyAdapter test endpoints")
    app.include_router(
        dummy_adapter_status.router,
        prefix=f"/{API_VERSION}",
        tags=["test endpoints for DummyAdapter"],
    )
