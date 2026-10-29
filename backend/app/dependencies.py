"""Application-wide singletons, wired once."""
from app.config import DB_PATH, ROOM_EMPTY_GRACE
from app.database.connection import Database
from app.database.repository import MatchRepository
from app.game.registry import RoomRegistry
from app.websocket.manager import ConnectionManager

database = Database(DB_PATH)
repository = MatchRepository(database)
manager = ConnectionManager()


async def _persist_match(room, leaderboard: list[dict]) -> None:
    await repository.save_match(room.id, room.settings.rounds, leaderboard)


registry = RoomRegistry(manager, on_game_over=_persist_match, empty_grace=ROOM_EMPTY_GRACE)
