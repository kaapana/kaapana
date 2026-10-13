import asyncio
import logging
from contextlib import asynccontextmanager

from app.config import get_settings
from app.dependencies import get_connection_manager, get_wopi
from app.model.websockets import ConnectionManager
from app.model.wopi import WOPI
from app.routers.documents import router as document
from app.routers.wopi import router as wopi
from app.routers.wopi_control import router as wopi_control
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles

log = logging.getLogger("uvicorn.error")
if get_settings().dev_mode:
    log.warning("DEV mode active, disable for production!")
    log.setLevel(logging.DEBUG)
else:
    log.setLevel(logging.INFO)


async def wopi_discovery_task(wopi_srv: WOPI) -> None:
    settings = get_settings()
    while True:
        try:
            await run_in_threadpool(wopi_srv.fetch_apps)
        except Exception as error:
            log.warning("WOPI discovery failed: %s", error)
        await asyncio.sleep(settings.discovery_interval_seconds if wopi_srv.apps else settings.discovery_retry_seconds)


@asynccontextmanager
async def lifespan(app: FastAPI):
    discovery = asyncio.create_task(wopi_discovery_task(get_wopi()))
    yield
    discovery.cancel()


app = FastAPI(lifespan=lifespan)

if get_settings().dev_mode:
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


app.include_router(wopi, prefix="/wopi")
app.include_router(wopi_control, prefix="/wopi-discovery")
app.include_router(document, prefix="/documents")


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    con_mgr: ConnectionManager = Depends(get_connection_manager),
):
    await con_mgr.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        con_mgr.disconnect(websocket)


app.mount("/", StaticFiles(directory=get_settings().ui_directory, html=True, check_dir=False), name="static")
