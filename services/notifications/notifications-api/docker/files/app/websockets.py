import functools

from app.notifications.schemas import NotificationDispatch
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_notifications_to_users(
        self, notification_item: NotificationDispatch, users_list: list[str]
    ) -> tuple:
        notification_json = notification_item.model_dump(mode="json")

        active_conn = len(self.active_connections)
        filtered_connections = []
        for connection in self.active_connections:
            if connection.headers.get("x-forwarded-user") in users_list:
                filtered_connections.append(connection)

        for connection in filtered_connections:
            await connection.send_json(notification_json)

        return len(filtered_connections), active_conn

    async def broadcast_notifications(
        self, notification_item: NotificationDispatch
    ) -> tuple:

        active_conn = len(self.active_connections)
        notification_json = notification_item.model_dump(mode="json")
        for connection in self.active_connections:
            await connection.send_json(notification_json)

        return active_conn, active_conn


@functools.lru_cache()
def get_connection_manager() -> ConnectionManager:
    return ConnectionManager()
