import os
import sqlite3
from contextlib import contextmanager
from typing import Iterator

from app.database.models import SCHEMA


class Database:
    """Opens short-lived SQLite connections (safe to use from worker threads)."""

    def __init__(self, path: str) -> None:
        self.path = path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_schema(self) -> None:
        folder = os.path.dirname(os.path.abspath(self.path))
        os.makedirs(folder, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
