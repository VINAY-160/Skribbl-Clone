import asyncio

from app.database.connection import Database


class MatchRepository:
    """Saves finished matches and reads leaderboard data.

    Public methods are async and push the blocking sqlite3 work onto a thread.
    """

    def __init__(self, database: Database) -> None:
        self._db = database

    async def save_match(self, room_id: str, rounds: int, leaderboard: list[dict]) -> int:
        return await asyncio.to_thread(self._save_match, room_id, rounds, leaderboard)

    async def top_players(self, limit: int = 20) -> list[dict]:
        return await asyncio.to_thread(self._top_players, limit)

    async def recent_matches(self, limit: int = 10) -> list[dict]:
        return await asyncio.to_thread(self._recent_matches, limit)

    # ---- blocking implementations
    def _save_match(self, room_id: str, rounds: int, leaderboard: list[dict]) -> int:
        winner = next((e["name"] for e in leaderboard if e["rank"] == 1), None)
        with self._db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO matches (room_id, rounds, player_count, winner_name) VALUES (?, ?, ?, ?)",
                (room_id, rounds, len(leaderboard), winner),
            )
            match_id = cur.lastrowid
            conn.executemany(
                "INSERT INTO match_players (match_id, player_name, score, rank) VALUES (?, ?, ?, ?)",
                [(match_id, e["name"], e["score"], e["rank"]) for e in leaderboard],
            )
        return match_id

    def _top_players(self, limit: int) -> list[dict]:
        with self._db.connect() as conn:
            rows = conn.execute(
                """SELECT player_name AS name, COUNT(*) AS games,
                          SUM(CASE WHEN rank = 1 THEN 1 ELSE 0 END) AS wins,
                          SUM(score) AS total_score, MAX(score) AS best_score
                   FROM match_players GROUP BY player_name
                   ORDER BY wins DESC, total_score DESC LIMIT ?""",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def _recent_matches(self, limit: int) -> list[dict]:
        with self._db.connect() as conn:
            rows = conn.execute(
                "SELECT id, room_id, rounds, player_count, winner_name, played_at "
                "FROM matches ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
