import logging
from contextlib import asynccontextmanager

from app.api.v1.routers import health_check, workflow_runs, workflows
from app.database import async_engine
from app.dependencies import get_connection_manager
from app.logging_config import setup_logging
from app.models import Base
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

setup_logging()
logger = logging.getLogger(__name__)

API_VERSION = "v1"


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


# Versioned routers
app.include_router(
    workflow_runs.router, prefix=f"/{API_VERSION}", tags=["workflow runs"]
)
app.include_router(workflows.router, prefix=f"/{API_VERSION}", tags=["workflow"])
app.include_router(health_check.router, prefix=f"/{API_VERSION}", tags=["health"])
