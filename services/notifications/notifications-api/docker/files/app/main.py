import logging

from app.health.routes import router as health_router
from app.notifications.routes import router as notification_router
from app.websockets import ConnectionManager, get_connection_manager
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi_versioning import VersionedFastAPI, version

logger = logging.getLogger(__name__)

app = FastAPI(
    root_path="/notifications-api",
    title="notifications-api",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)

app.include_router(health_router, prefix="/health")
app.include_router(notification_router, prefix="/dispatch")

app = VersionedFastAPI(app, version_format="{major}", prefix_format="/v{major}")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    # print("Connection request recieved")
    await con_mgr.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        con_mgr.disconnect(websocket)
