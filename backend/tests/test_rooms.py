def test_create_and_get_room(client):
    r = client.post("/api/rooms", json={"settings": {"rounds": 4, "is_private": False}})
    assert r.status_code == 201
    room_id = r.json()["room_id"]
    assert len(room_id) == 6
    info = client.get(f"/api/rooms/{room_id.lower()}").json()
    assert info["rounds"] == 4 and info["phase"] == "lobby"


def test_unknown_room_404(client):
    assert client.get("/api/rooms/NOPE00").status_code == 404


def test_invalid_settings_rejected(client):
    assert client.post("/api/rooms", json={"settings": {"rounds": 99}}).status_code == 422
    assert client.post("/api/rooms", json={"settings": {"max_players": 1}}).status_code == 422
    assert client.post("/api/rooms", json={"settings": {"draw_time": 5}}).status_code == 422


def test_leaderboard_endpoints(client):
    assert client.get("/api/leaderboard").status_code == 200
    assert client.get("/api/leaderboard/matches").status_code == 200
    assert client.get("/api/health").json() == {"status": "ok"}
