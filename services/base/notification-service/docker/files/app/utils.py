from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder







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

    async def notify_user(self, user_ids: list[str], message) -> None:
        json_message = jsonable_encoder(message)
        for user_id in user_ids:
            for connection in self.active_connections.get(user_id, []):
                await connection.send_json(json_message)
