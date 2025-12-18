from fastapi import APIRouter, Depends, WebSocket
from starlette.websockets import WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_db
from app.api.v1.endpoints import artifacts, entities, maintenance, metadata, queries
from app.services.event_bus import get_event_bus


router = APIRouter()

router.include_router(entities.router)
router.include_router(metadata.router)
router.include_router(artifacts.router)
router.include_router(queries.router)
router.include_router(maintenance.router)


@router.get("/health", summary="Health check")
async def health_check(
    db: AsyncSession = Depends(get_async_db),
) -> dict:  # noqa: ARG001
    return {"status": "ok"}


@router.websocket("/ws/events")
async def events_websocket(websocket: WebSocket) -> None:
    bus = get_event_bus()
    await bus.connect(websocket)
    try:
        while True:
            try:
                await websocket.receive_text()
            except WebSocketDisconnect:
                break
    finally:
        await bus.disconnect(websocket)
