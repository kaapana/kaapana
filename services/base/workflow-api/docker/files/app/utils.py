from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from uuid import UUID
from pydantic import BaseModel



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


