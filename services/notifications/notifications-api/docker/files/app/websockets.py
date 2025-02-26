from app.notifications.schemas import NotificationDispatch
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(len(self.active_connections))

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_notifications(self, notification_item: NotificationDispatch):
        notification_json = notification_item.model_dump(mode="json")
        for connection in self.active_connections:
            await connection.send_json(notification_json)
