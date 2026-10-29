"""MessageHandler (event router per connection) and the /ws endpoint."""
import json
import logging

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.dependencies import manager, registry
from app.game.errors import GameError
from app.game.player import Player
from app.game.room import Room
from app.schemas.game import ClientEvent as C, ServerEvent as E

log = logging.getLogger(__name__)
ws_router = APIRouter()


class MessageHandler:
    """One per connection. Maps incoming events to room/engine actions."""

    def __init__(self, room: Room, player: Player) -> None:
        self.room = room
        self.player = player
        self.engine = room.engine
        self._routes = {
            C.PING: self.on_ping, C.SYNC: self.on_sync, C.READY: self.on_ready,
            C.UPDATE_SETTINGS: self.on_update_settings, C.START_GAME: self.on_start_game,
            C.WORD_CHOSEN: self.on_word_chosen,
            C.DRAW_START: self.on_draw_start, C.DRAW_MOVE: self.on_draw_move,
            C.DRAW_END: self.on_draw_end, C.CANVAS_CLEAR: self.on_canvas_clear,
            C.DRAW_UNDO: self.on_draw_undo,
            C.GUESS: self.on_text, C.CHAT: self.on_text,
            C.KICK: self.on_kick, C.BAN: self.on_ban, C.VOTEKICK: self.on_votekick,
        }

    async def handle(self, message) -> None:
        if not isinstance(message, dict):
            return await self._error("Invalid message")
        data = message.get("data") or {}
        try:
            route = self._routes.get(C(message.get("event")))
        except ValueError:
            route = None
        if route is None or not isinstance(data, dict):
            return await self._error("Unknown event")
        try:
            await route(data)
        except GameError as exc:
            await self._error(str(exc))

    async def _error(self, text: str) -> None:
        await self.room.send(self.player.id, E.ERROR, {"message": text})

    # ---- lobby
    async def on_ping(self, data): await self.room.send(self.player.id, E.PONG)
    async def on_sync(self, data):
        await self.room.send(self.player.id, E.GAME_STATE, self.room.state_for(self.player.id))
    async def on_ready(self, data): await self.room.set_ready(self.player, data.get("ready", True))
    async def on_update_settings(self, data): await self.room.update_settings(self.player, data)
    async def on_start_game(self, data): await self.engine.start_game(self.player)

    # ---- game
    async def on_word_chosen(self, data):
        await self.engine.choose_word(self.player, data.get("word", data.get("index")))
    async def on_draw_start(self, data): await self.engine.draw_start(self.player, data)
    async def on_draw_move(self, data): await self.engine.draw_move(self.player, data)
    async def on_draw_end(self, data): await self.engine.draw_end(self.player)
    async def on_canvas_clear(self, data): await self.engine.clear_canvas(self.player)
    async def on_draw_undo(self, data): await self.engine.undo(self.player)
    async def on_text(self, data): await self.engine.handle_text(self.player, str(data.get("text", "")))

    # ---- moderation
    async def on_kick(self, data): await self.room.kick(self.player, str(data.get("player_id", "")))
    async def on_ban(self, data): await self.room.kick(self.player, str(data.get("player_id", "")), ban=True)
    async def on_votekick(self, data): await self.room.votekick(self.player, str(data.get("player_id", "")))


@ws_router.websocket("/ws/{room_id}")
async def game_socket(ws: WebSocket, room_id: str,
                      name: str = Query("", max_length=40),
                      player_id: str | None = Query(None, max_length=32)) -> None:
    await ws.accept()
    room = registry.get(room_id)
    if room is None:
        await ws.send_json({"event": E.ERROR.value, "data": {"message": "Room not found"}})
        await ws.close(code=4404)
        return
    try:
        player, reconnected = room.join(name, player_id)
    except GameError as exc:
        await ws.send_json({"event": E.ERROR.value, "data": {"message": str(exc)}})
        await ws.close(code=4403)
        return

    await manager.connect(room.id, player.id, ws)
    await room.on_player_joined(player, reconnected)
    handler = MessageHandler(room, player)
    try:
        while True:
            text = await ws.receive_text()
            try:
                message = json.loads(text)
            except ValueError:
                await handler.handle(None)
                continue
            await handler.handle(message)
    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("websocket crashed")
    finally:
        if manager.disconnect(room.id, player.id, ws):
            await room.on_player_disconnected(player)
            registry.schedule_cleanup(room)
