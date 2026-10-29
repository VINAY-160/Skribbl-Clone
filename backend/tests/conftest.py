import os
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(), "test.db")

import pytest
from fastapi.testclient import TestClient

from app.game.engine import GameEngine


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(GameEngine, "TURN_END_DELAY", 0.1)
    from app.main import app
    with TestClient(app) as c:
        yield c
