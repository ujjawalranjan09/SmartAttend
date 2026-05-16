from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import asyncio
import json

router = APIRouter()

# In-memory connection registry: session_id -> set of websockets
_connections: Dict[str, Set[WebSocket]] = {}


async def broadcast_to_session(session_id: str, message: dict):
    """Push attendance event to all faculty/admin watching this session."""
    sockets = _connections.get(session_id, set())
    dead = set()
    for ws in sockets:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.add(ws)
    _connections[session_id] -= dead


@router.websocket("/session/{session_id}")
async def session_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in _connections:
        _connections[session_id] = set()
    _connections[session_id].add(websocket)
    try:
        while True:
            # Keep connection alive; receive pings
            data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
            if data == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, asyncio.TimeoutError):
        _connections[session_id].discard(websocket)
