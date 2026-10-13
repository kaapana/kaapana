import logging
from collections import defaultdict

from fastapi import WebSocket

log = logging.getLogger("uvicorn.error")


class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, set[WebSocket]] = defaultdict(set)

    async def connect(self, websocket: WebSocket, bucket: str):
        await websocket.accept()
        self.active_connections[bucket].add(websocket)

    def disconnect(self, websocket: WebSocket, bucket: str):
        connections = self.active_connections.get(bucket)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            del self.active_connections[bucket]

    async def announce_documents(self, bucket: str):
        for connection in list(self.active_connections.get(bucket, ())):
            try:
                await connection.send_json({"type": "update"})
            except Exception as error:
                log.debug("Dropping document update socket: %s", error)
                self.disconnect(connection, bucket)
