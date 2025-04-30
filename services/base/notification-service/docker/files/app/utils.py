import requests
from app.config import settings
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder


class AiiHelper:
    def __init__(self, base_url: str = settings.AII_SERVICE_URL):
        self.base_url = base_url

    async def fetch_user_ids(self, project_id: str) -> list[str]:
        response = requests.get(f"{self.base_url}/projects/{project_id}/users")
        if response.status_code == 404:
            return None
        response.raise_for_status()
        try:
            data = response.json()
        except requests.JSONDecodeError:
            data = []

        return [user["id"] for user in data]

    async def user_exists(self, user_id: str) -> bool:
        response = requests.get(f"{self.base_url}/users/{user_id}")
        if response.status_code < 300:
            return True
        elif response.status_code == 404:
            return False
        else:
            response.raise_for_status()
            raise Exception("THis should not happen")


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
