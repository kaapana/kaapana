import logging

from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from app.notifications.v1.routes import router as router_v1
from app.notifications.v2.routes import router as router_v2
from app.dependencies import get_connection_manager
from app.database import async_engine
from app.models import Base
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="Notification Service",
    version="0.1.0",
    summary="""
Send notifications to individual users or groups of users in the local platform
(e.g. when workflow failed, an update is available, ...)
""",
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


app.include_router(router_v1, prefix="/v1", tags=["v1"], deprecated=True)
app.include_router(router_v2, prefix="/v2", tags=["v2"])
