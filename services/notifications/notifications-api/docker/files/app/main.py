import functools
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime

from app.database.queries import verify_postgres_conn
from app.notifications.schemas import Notification, NotificationDispatch
from app.websockets import ConnectionManager
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


app = FastAPI(
    root_path="/notifications-api",
    title="notifications-api",
    docs_url="/docs",
    openapi_url="/openapi.json",
    version="0.1.0",
)


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()


@app.get("/v1/health/check-db-connection", tags=["Health"])
async def check_db_connection():
    verified, err = await verify_postgres_conn()
    if verified:
        return {"status": "Database connection successful"}
    else:
        raise HTTPException(
            status_code=500, detail=f"Database connection failed, {err}"
        )


@app.post(
    "/v1/dispatch/project/{project_id}",
    response_model=NotificationDispatch,
    tags=["Dispatch"],
)
async def get_keycloak_user_by_id(
    project_id: str,
    notification_item: Notification,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    dispatch = NotificationDispatch(
        id=uuid.uuid4(),
        user_id="",
        project=project_id,
        timestamp=datetime.now(),
        **notification_item.dict(),  # Unpack the remaining fields from Notification
    )

    await con_mgr.send_notifications(dispatch)
    return dispatch


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    print("Connection request recieved")
    print(websocket)
    await con_mgr.connect(websocket)
    try:
        while True:
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        con_mgr.disconnect(websocket)
