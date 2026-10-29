import asyncio
import logging

from fastapi import WebSocket

log = logging.getLogger(__name__)


class ConnectionManager:
    """Owns the live sockets: room_id -> {player_id: WebSocket}. Knows nothing about game rules."""

    def __init__(self) -> None:
        self._rooms: dict[str, dict[str, WebSocket]] = {}

    async def connect(self, room_id: str, player_id: str, ws: WebSocket) -> None:
        conns = self._rooms.setdefault(room_id, {})
        old = conns.get(player_id)
        conns[player_id] = ws
        if old is not None and old is not ws:  # same player reconnecting from a new tab
            try:
                await old.close(code=4000)
            except Exception:
                pass

    def disconnect(self, room_id: str, player_id: str, ws: WebSocket) -> bool:
        """Returns True only if `ws` was the player's current socket."""
        conns = self._rooms.get(room_id)
        if not conns or conns.get(player_id) is not ws:
            return False
        del conns[player_id]
        if not conns:
            del self._rooms[room_id]
        return True

    async def send(self, room_id: str, player_id: str, event, data: dict | None = None) -> None:
        ws = self._rooms.get(room_id, {}).get(player_id)
        if ws is not None:
            await self._safe_send(ws, self._envelope(event, data))

    async def broadcast(self, room_id: str, event, data: dict | None = None, exclude=None) -> None:
        skip = set(exclude or ())
        msg = self._envelope(event, data)
        targets = [ws for pid, ws in list(self._rooms.get(room_id, {}).items()) if pid not in skip]
        if targets:
            await asyncio.gather(*(self._safe_send(ws, msg) for ws in targets))

    async def close(self, room_id: str, player_id: str, code: int = 1000) -> None:
        ws = self._rooms.get(room_id, {}).get(player_id)
        if ws is not None:
            try:
                await ws.close(code=code)
            except Exception:
                pass

    @staticmethod
    def _envelope(event, data) -> dict:
        return {"event": getattr(event, "value", event), "data": data or {}}

    @staticmethod
    async def _safe_send(ws: WebSocket, message: dict) -> None:
        try:
            await ws.send_json(message)
        except Exception:
            log.debug("send failed (socket probably closed)")
