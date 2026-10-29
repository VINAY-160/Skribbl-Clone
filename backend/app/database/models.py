"""Persistent tables. Live game state is in memory; only finished matches are stored."""

SCHEMA = """
CREATE TABLE IF NOT EXISTS matches (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    room_id      TEXT    NOT NULL,
    rounds       INTEGER NOT NULL,
    player_count INTEGER NOT NULL,
    winner_name  TEXT,
    played_at    TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS match_players (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    match_id    INTEGER NOT NULL REFERENCES matches(id) ON DELETE CASCADE,
    player_name TEXT    NOT NULL,
    score       INTEGER NOT NULL,
    rank        INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_match_players_name ON match_players(player_name);
"""
