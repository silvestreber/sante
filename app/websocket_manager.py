"""Gestor de conexiones WebSocket para notificaciones en tiempo real.

Permite enviar mensajes push a usuarios concretos a través de WebSocket.
Cada usuario puede tener múltiples conexiones activas simultáneas (p.ej.
varias pestañas del navegador).

Uso típico:
    1. El cliente abre una conexión WebSocket a /api/notifications/ws?token=<jwt>.
    2. El servidor llama a manager.connect(websocket, user_id).
    3. Cuando se crea una notificación, se llama a manager.send_to_user(user_id, data).
    4. Al desconectarse, manager.disconnect(websocket, user_id) limpia el registro.

La instancia global `manager` es importada por el router de notificaciones.
"""
from fastapi import WebSocket
import json


class ConnectionManager:
    """Gestiona las conexiones WebSocket activas de todos los usuarios.

    Mantiene un diccionario {user_id: [WebSocket, ...]} para poder enviar
    mensajes a un usuario específico aunque tenga varias pestañas abiertas.
    Los errores de envío se silencian para no interrumpir otras conexiones.
    """
    def __init__(self):
        # user_id -> list of active websocket connections
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, data: dict):
        if user_id in self.active_connections:
            message = json.dumps(data)
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_text(message)
                except Exception:
                    pass


manager = ConnectionManager()
