import logging
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager

from app.logging_config import setup_logging
from app.api.v1.routers import workflow_runs, workflows
from app.dependencies import get_connection_manager
from app.database import async_engine
from app.models import Base

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


# Versioned routers
app.include_router(
    workflow_runs.router, prefix=f"/{API_VERSION}", tags=["workflow runs"]
)
app.include_router(workflows.router, prefix=f"/{API_VERSION}", tags=["workflow"])
