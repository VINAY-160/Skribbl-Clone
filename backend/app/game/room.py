"""Room: membership, host powers, messaging helpers. Owns one GameEngine."""
from __future__ import annotations

import logging
import random
import secrets
import time
from typing import Awaitable, Callable, Iterable

from pydantic import ValidationError

from app.game.engine import GameEngine, Phase
from app.game.errors import GameError
from app.game.player import Player
from app.schemas.game import ServerEvent as E
from app.schemas.room import RoomSettings
from app.websocket.manager import ConnectionManager

log = logging.getLogger(__name__)

GameOverCallback = Callable[["Room", list[dict]], Awaitable[None]]


class Room:
    MAX_NAME = 20

    def __init__(self, room_id: str, settings: RoomSettings, manager: ConnectionManager,
                 on_game_over: GameOverCallback | None = None) -> None:
        self.id = room_id
        self.settings = settings
        self.players: dict[str, Player] = {}
        self.host_id: str | None = None
        self.banned_names: set[str] = set()
        self.created_at = time.time()
        self._manager = manager
        self._on_game_over = on_game_over
        self.engine = GameEngine(self)

    # ---------------------------------------------------------- properties
    @property
    def phase(self) -> Phase:
        return self.engine.phase

    @property
    def is_full(self) -> bool:
        return len(self.players) >= self.settings.max_players

    def connected_players(self) -> list[Player]:
        return [p for p in self.players.values() if p.connected]

    # ----------------------------------------------------------- membership
    def join(self, name: str, player_id: str | None = None) -> tuple[Player, bool]:
        """Returns (player, reconnected)."""
        if player_id and player_id in self.players:
            player = self.players[player_id]
            player.connected = True
            return player, True
        name = " ".join((name or "").split())[: self.MAX_NAME]
        if not name:
            raise GameError("Name is required")
        if name.lower() in self.banned_names:
            raise GameError("You are banned from this room")
        if self.is_full:
            raise GameError("Room is full")
        player = Player(secrets.token_urlsafe(6), self._unique_name(name), avatar=random.randrange(12))
        self.players[player.id] = player
        if self.host_id is None:
            self.host_id = player.id
        return player, False

    def _unique_name(self, name: str) -> str:
        taken = {p.name.lower() for p in self.players.values()}
        candidate, n = name, 2
        while candidate.lower() in taken:
            candidate = f"{name} ({n})"
            n += 1
        return candidate

    def _reassign_host(self) -> None:
        current = self.players.get(self.host_id)
        if current and current.connected:
            return
        self.host_id = next((p.id for p in self.players.values() if p.connected), None)

    async def on_player_joined(self, player: Player, reconnected: bool) -> None:
        await self.send(player.id, E.JOINED, {
            "player_id": player.id, "room_id": self.id, "state": self.state_for(player.id)})
        if reconnected:
            await self.broadcast(E.PLAYERS_UPDATE, {"players": self.players_payload(),
                                                    "host_id": self.host_id})
            return
        await self.broadcast(E.PLAYER_JOINED, {"player": self.player_payload(player),
                                               "players": self.players_payload()},
                             exclude={player.id})
        await self.system_message(f"{player.name} joined the room", exclude={player.id})

    async def on_player_disconnected(self, player: Player) -> None:
        if self.players.get(player.id) is not player:
            return  # already removed (kicked)
        player.connected = False
        if self.phase in (Phase.LOBBY, Phase.GAME_OVER):
            del self.players[player.id]
        if player.id == self.host_id:
            self._reassign_host()
        await self.broadcast(E.PLAYER_LEFT, {"player_id": player.id,
                                             "players": self.players_payload(),
                                             "host_id": self.host_id})
        await self.system_message(f"{player.name} left the room")
        await self.engine.on_player_left(player)

    # ------------------------------------------------------------ host powers
    def _require_host(self, player: Player) -> None:
        if player.id != self.host_id:
            raise GameError("Only the host can do that")

    async def update_settings(self, requester: Player, raw: dict) -> None:
        self._require_host(requester)
        if self.phase not in (Phase.LOBBY, Phase.GAME_OVER):
            raise GameError("Settings can only be changed in the lobby")
        try:
            new = RoomSettings.model_validate({**self.settings.model_dump(), **raw})
        except ValidationError:
            raise GameError("Invalid settings")
        if new.max_players < len(self.players):
            raise GameError("Max players is lower than the current player count")
        self.settings = new
        await self.broadcast(E.SETTINGS_UPDATED, {"settings": self.public_settings()})

    async def set_ready(self, player: Player, ready: bool) -> None:
        if self.phase in (Phase.LOBBY, Phase.GAME_OVER):
            player.ready = bool(ready)
            await self.broadcast(E.PLAYERS_UPDATE, {"players": self.players_payload(),
                                                    "host_id": self.host_id})

    async def kick(self, requester: Player, target_id: str, ban: bool = False) -> None:
        self._require_host(requester)
        target = self.players.get(target_id)
        if target is None or target.id == requester.id:
            raise GameError("Invalid target")
        await self._evict(target, ban)

    async def votekick(self, voter: Player, target_id: str) -> None:
        target = self.players.get(target_id)
        if target is None or target.id == voter.id:
            raise GameError("Invalid target")
        voters = [p for p in self.connected_players() if p.id != target.id]
        if len(voters) < 2:
            raise GameError("Votekick needs at least 3 players")
        target.kick_votes.add(voter.id)
        needed = len(voters) // 2 + 1
        votes = len(target.kick_votes & {p.id for p in voters})
        if votes >= needed:
            await self._evict(target, ban=False)
        else:
            await self.system_message(f"{voter.name} voted to kick {target.name} ({votes}/{needed})")

    async def _evict(self, target: Player, ban: bool) -> None:
        if ban:
            self.banned_names.add(target.name.lower())
        self.players.pop(target.id, None)  # remove first so the socket-close path is a no-op
        target.connected = False
        await self.send(target.id, E.KICKED, {"banned": ban})
        await self._manager.close(self.id, target.id, code=4001)
        await self.broadcast(E.PLAYER_LEFT, {"player_id": target.id,
                                             "players": self.players_payload(),
                                             "host_id": self.host_id})
        await self.system_message(f"{target.name} was {'banned' if ban else 'kicked'}")
        await self.engine.on_player_left(target)

    # --------------------------------------------------------------- payloads
    def public_settings(self) -> dict:
        # custom words are excluded so guessers can't read the word pool
        return self.settings.model_dump(mode="json", exclude={"custom_words"})

    def player_payload(self, p: Player) -> dict:
        return {**p.to_dict(), "is_host": p.id == self.host_id,
                "is_drawer": p.id == self.engine.drawer_id}

    def players_payload(self) -> list[dict]:
        return [self.player_payload(p) for p in self.players.values()]

    def state_for(self, player_id: str) -> dict:
        e = self.engine
        is_drawer = player_id == e.drawer_id
        reveal = is_drawer or e.phase in (Phase.TURN_END,)
        return {
            "room_id": self.id, "phase": e.phase.value, "round": e.round_no,
            "total_rounds": self.settings.rounds, "drawer_id": e.drawer_id,
            "time_left": e.time_left, "hint": e.hint,
            "word": e.word if reveal else None,
            "word_options": e.word_options if (is_drawer and e.phase == Phase.CHOOSING) else None,
            "players": self.players_payload(), "host_id": self.host_id,
            "settings": self.public_settings(), "strokes": e.canvas.to_list(),
        }

    def info(self) -> dict:
        return {"room_id": self.id, "is_private": self.settings.is_private,
                "phase": self.phase.value, "player_count": len(self.players),
                "max_players": self.settings.max_players, "rounds": self.settings.rounds,
                "draw_time": self.settings.draw_time}

    # -------------------------------------------------------------- messaging
    async def send(self, player_id: str, event, data: dict | None = None) -> None:
        await self._manager.send(self.id, player_id, event, data)

    async def send_many(self, player_ids: Iterable[str], event, data: dict | None = None) -> None:
        for pid in set(player_ids):
            await self._manager.send(self.id, pid, event, data)

    async def broadcast(self, event, data: dict | None = None, exclude=None) -> None:
        await self._manager.broadcast(self.id, event, data, exclude)

    async def system_message(self, text: str, exclude=None) -> None:
        await self.broadcast(E.CHAT_MESSAGE, {"kind": "system", "text": text}, exclude=exclude)

    async def game_finished(self, leaderboard: list[dict]) -> None:
        if self._on_game_over:
            try:
                await self._on_game_over(self, leaderboard)
            except Exception:
                log.exception("failed to persist match result")

    def shutdown(self) -> None:
        self.engine.shutdown()
