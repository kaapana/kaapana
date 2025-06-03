from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from uuid import UUID
from pydantic import BaseModel


class Event(BaseModel):
    type: str
    notification_id: UUID


class EventNew(Event):
    type: str = "new"


class EventRead(Event):
    type: str = "read"


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        user_id = websocket.headers.get("x-forwarded-user")
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket):
        user_id = websocket.headers.get("x-forwarded-user")
        self.active_connections[user_id].remove(websocket)

    async def notify_new_notification(self, user_ids: list[str], id: UUID) -> None:
        await self.send(user_ids=user_ids, event=EventNew(notification_id=id))

    async def notify_read_notification(self, user_ids: list[str], id: UUID) -> None:
        await self.send(user_ids=user_ids, event=EventRead(notification_id=id))

    async def send(self, user_ids: list[str], event: Event) -> None:
        json_message = jsonable_encoder(event)
        for user_id in user_ids:
            for connection in self.active_connections.get(user_id, []):
                await connection.send_json(json_message)
