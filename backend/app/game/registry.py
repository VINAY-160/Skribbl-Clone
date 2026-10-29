"""RoomRegistry: creates, finds and garbage-collects rooms."""
import asyncio
import secrets

from app.game.room import GameOverCallback, Room
from app.schemas.room import RoomSettings
from app.websocket.manager import ConnectionManager


class RoomRegistry:
    ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I confusion
    CODE_LENGTH = 6

    def __init__(self, manager: ConnectionManager, on_game_over: GameOverCallback | None = None,
                 empty_grace: float = 60) -> None:
        self._manager = manager
        self._on_game_over = on_game_over
        self._empty_grace = empty_grace
        self._rooms: dict[str, Room] = {}
        self._cleanup_tasks: set[asyncio.Task] = set()

    def _new_code(self) -> str:
        while True:
            code = "".join(secrets.choice(self.ALPHABET) for _ in range(self.CODE_LENGTH))
            if code not in self._rooms:
                return code

    def create(self, settings: RoomSettings) -> Room:
        room = Room(self._new_code(), settings, self._manager, self._on_game_over)
        self._rooms[room.id] = room
        self.schedule_cleanup(room)  # removed if nobody ever joins
        return room

    def get(self, room_id: str) -> Room | None:
        return self._rooms.get((room_id or "").upper())

    def list_public(self) -> list[Room]:
        return [r for r in self._rooms.values()
                if not r.settings.is_private and not r.is_full and r.connected_players()]

    def remove(self, room_id: str) -> None:
        room = self._rooms.pop(room_id, None)
        if room:
            room.shutdown()

    def schedule_cleanup(self, room: Room) -> None:
        if room.connected_players():
            return

        async def _cleanup() -> None:
            await asyncio.sleep(self._empty_grace)
            current = self._rooms.get(room.id)
            if current is room and not room.connected_players():
                self.remove(room.id)

        task = asyncio.create_task(_cleanup())
        self._cleanup_tasks.add(task)
        task.add_done_callback(self._cleanup_tasks.discard)
