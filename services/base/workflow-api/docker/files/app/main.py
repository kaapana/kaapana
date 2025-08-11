import logging

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from app.api.workflows import router as workflow_router
from app.api.workflow_runs import router as workflow_run_router
from app.dependencies import get_connection_manager
from app.database import async_engine
from app.adapters.config import celery_app
from app.models import Base
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

tags_metadata = [
    {
        "name": "workflow",
        "description": "Search for workflow-related resources.",
    }
]

app = FastAPI(
    title="Kaapana Workflow API",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.0.1",
    openapi_tags=tags_metadata,
    lifespan=lifespan,
)


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    con_mgr=Depends(get_connection_manager),
):
    await con_mgr.connect(websocket)
    try:
        while True:
            # No server operations
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        con_mgr.disconnect(websocket)

app.include_router(workflow_run_router, prefix="/v1", tags=["workflow runs"])
app.include_router(workflow_router, prefix="/v1", tags=["workflow"])


