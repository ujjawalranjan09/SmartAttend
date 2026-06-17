from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Dict, Set
import asyncio
import json

from app.core.security import decode_token

router = APIRouter()

# In-memory connection registry: session_id -> set of websockets
_connections: Dict[str, Set[WebSocket]] = {}

# Notification connections: user_id -> set of websockets
_notif_connections: Dict[str, Set[WebSocket]] = {}


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


async def broadcast_to_user(user_id: str, message: dict):
    """Push notification to all WebSocket connections for a given user."""
    sockets = _notif_connections.get(user_id, set())
    dead = set()
    for ws in sockets:
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            dead.add(ws)
    _notif_connections[user_id] -= dead


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


@router.websocket("/notifications/{user_id}")
async def notifications_websocket(
    websocket: WebSocket,
    user_id: str,
    token: str = Query(...),
):
    """WebSocket endpoint for real-time notifications.

    Clients connect with ?token=XXX. The JWT is validated; if invalid
    the connection is closed with code 4001.
    """
    try:
        payload = decode_token(token)
        if payload.get("sub") != user_id:
            await websocket.close(code=4001, reason="Token does not match user")
            return
    except (ValueError, Exception):
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    await websocket.accept()
    if user_id not in _notif_connections:
        _notif_connections[user_id] = set()
    _notif_connections[user_id].add(websocket)
    try:
        while True:
            data = await asyncio.wait_for(websocket.receive_text(), timeout=60)
            if data == "ping":
                await websocket.send_text("pong")
    except (WebSocketDisconnect, asyncio.TimeoutError):
        _notif_connections[user_id].discard(websocket)
