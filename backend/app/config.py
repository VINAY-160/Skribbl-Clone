"""Central configuration, read from environment variables."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
WORDS_PATH = BASE_DIR / "data" / "words.json"
DB_PATH = os.getenv("DB_PATH", str(BASE_DIR.parent / "skribbl.db"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]
ROOM_EMPTY_GRACE = int(os.getenv("ROOM_EMPTY_GRACE", "60"))
