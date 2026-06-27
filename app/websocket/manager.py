from fastapi import WebSocket


# class ConnectionManager:
#     def __init__(self):
#         self.connections: dict[str, set[WebSocket]] = {}

#     async def connect(self, user_id: str, websocket: WebSocket):
#         await websocket.accept()
#         if user_id not in self.connections:
#             self.connections[user_id] = set()

#         self.connections[user_id].add(websocket)

#     def disconnect(self, user_id: str):
#         self.connections.pop(user_id, None)

#     async def send(self, user_id: str, data: dict):
#         websocket = self.connections.get(user_id)

#         if websocket:
#             await websocket.send_json(data)

class ConnectionManager:
    def __init__(self):
        self.connections: dict[str, set[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()

        if user_id not in self.connections:
            self.connections[user_id] = set()

        self.connections[user_id].add(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.connections:
            self.connections[user_id].discard(websocket)

            if not self.connections[user_id]:
                del self.connections[user_id]

    async def send(self, user_id: str, data: dict):
        websockets = self.connections.get(user_id, set())

        for ws in list(websockets):
            try:
                await ws.send_json(data)
            except Exception:
                websockets.discard(ws)


# Global singleton
manager = ConnectionManager()
