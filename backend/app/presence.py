"""Single-worker room presence. Clients never submit positions over this channel."""

from .clock import utc_now
import asyncio
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy import select
from .database import Session
from .models import AuthSession, Character
from .security import digest

connections: dict[str, int] = {}


def read_presence(token, connected_ids):
    with Session() as db:
        auth = db.get(AuthSession, digest(token))
        if not auth or auth.expires < utc_now():
            return None
        c = db.scalar(select(Character).where(Character.account_id == auth.account_id))
        if not c:
            return None
        rows = db.scalars(
            select(Character).where(
                Character.room_id == c.room_id,
                Character.id.in_(connected_ids),
                Character.id != c.id,
            )
        ).all()
        return c.id, {
            "room_id": c.room_id,
            "players": [{"id": p.id, "name": p.name, "x": p.x, "y": p.y} for p in rows],
        }


async def room_socket(ws: WebSocket):
    await ws.accept()
    key = __import__("secrets").token_hex(12)
    try:
        # Token is the first message, avoiding tokens in request URLs/access logs.
        message = await asyncio.wait_for(ws.receive_json(), timeout=5)
        if not isinstance(message, dict):
            await ws.close(code=4401)
            return
        token = message.get("token", "")
        if not isinstance(token, str) or len(token) > 200:
            await ws.close(code=4401)
            return
        last = None
        while True:
            data = await asyncio.to_thread(
                read_presence, token, list(set(connections.values()))
            )
            if not data:
                await ws.close(code=4401)
                return
            character_id, payload = data
            if sum(v == character_id for k, v in connections.items() if k != key) >= 3:
                await ws.close(code=4429)
                return
            connections[key] = character_id
            if payload != last:
                await ws.send_json(payload)
                last = payload
            # Receive heartbeat to detect disconnects even when no position changes.
            try:
                heartbeat = await asyncio.wait_for(ws.receive_text(), timeout=0.5)
                if len(heartbeat) > 256:
                    await ws.close(code=4400)
                    return
            except asyncio.TimeoutError:
                pass
    except (
        WebSocketDisconnect,
        ValueError,
        TypeError,
        asyncio.TimeoutError,
        RuntimeError,
    ):
        pass
    finally:
        connections.pop(key, None)
