def recv(ws, event, limit=80):
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["event"] == event:
            return msg
    raise AssertionError(f"never received {event}")


def make_room(client, **settings):
    body = {"settings": {"rounds": 2, "draw_time": 20, "word_count": 2, "is_private": False, **settings}}
    return client.post("/api/rooms", json=body).json()["room_id"]


def test_full_turn_over_websockets(client):
    rid = make_room(client)
    with client.websocket_connect(f"/ws/{rid}?name=Alice") as a, \
         client.websocket_connect(f"/ws/{rid}?name=Bob") as b:
        ja, jb = recv(a, "joined")["data"], recv(b, "joined")["data"]
        socks = {ja["player_id"]: a, jb["player_id"]: b}
        assert ja["state"]["host_id"] == ja["player_id"]

        b.send_json({"event": "start_game", "data": {}})
        assert "host" in recv(b, "error")["data"]["message"].lower()

        a.send_json({"event": "start_game", "data": {}})
        rs = recv(a, "round_start")["data"]
        recv(b, "round_start")
        drawer = socks[rs["drawer_id"]]
        guesser = b if drawer is a else a

        options = recv(drawer, "word_options")["data"]["options"]
        drawer.send_json({"event": "word_chosen", "data": {"word": options[0]}})
        recv(drawer, "drawing_start")
        hint = recv(guesser, "drawing_start")["data"]["hint"]
        assert "_" in hint and options[0] not in hint

        guesser.send_json({"event": "draw_start", "data": {"x": 0.1, "y": 0.1}})
        assert "drawer" in recv(guesser, "error")["data"]["message"].lower()

        drawer.send_json({"event": "draw_start", "data": {"x": 0.1, "y": 0.2, "color": "#ff0000", "size": 4}})
        drawer.send_json({"event": "draw_move", "data": {"points": [[0.2, 0.3], [0.3, 0.4]]}})
        drawer.send_json({"event": "draw_end", "data": {}})
        assert recv(guesser, "draw_data")["data"]["type"] == "start"
        assert recv(guesser, "draw_data")["data"]["type"] == "move"

        guesser.send_json({"event": "guess", "data": {"text": "definitely not it"}})
        assert recv(drawer, "chat_message")["data"]["kind"] == "guess"

        guesser.send_json({"event": "guess", "data": {"text": f"  {options[0].upper()} "}})
        result = recv(guesser, "guess_result")["data"]
        assert result["correct"] and result["points"] > 0
        end = recv(guesser, "round_end")["data"]
        assert end["word"] == options[0] and end["reason"] == "all_guessed"


def test_late_joiner_gets_canvas_and_reconnect(client):
    rid = make_room(client)
    with client.websocket_connect(f"/ws/{rid}?name=Alice") as a:
        jid = recv(a, "joined")["data"]["player_id"]
    # lobby disconnect removes the player; reconnecting with the same name works
    with client.websocket_connect(f"/ws/{rid}?name=Alice") as a2:
        assert recv(a2, "joined")["data"]["state"]["phase"] == "lobby"


def test_kick_and_room_errors(client):
    rid = make_room(client)
    with client.websocket_connect(f"/ws/{rid}?name=Host") as h, \
         client.websocket_connect(f"/ws/{rid}?name=Guest") as g:
        recv(h, "joined")
        gid = recv(g, "joined")["data"]["player_id"]
        h.send_json({"event": "kick", "data": {"player_id": gid}})
        assert recv(g, "kicked")["data"]["banned"] is False

    with client.websocket_connect("/ws/ZZZZZZ?name=X") as bad:
        assert recv(bad, "error")["data"]["message"] == "Room not found"


def test_host_settings_update(client):
    rid = make_room(client)
    with client.websocket_connect(f"/ws/{rid}?name=Host") as h:
        recv(h, "joined")
        h.send_json({"event": "update_settings", "data": {"rounds": 5, "custom_words": ["secretword"]}})
        s = recv(h, "settings_updated")["data"]["settings"]
        assert s["rounds"] == 5 and "custom_words" not in s
        h.send_json({"event": "update_settings", "data": {"rounds": 99}})
        assert recv(h, "error")["data"]["message"] == "Invalid settings"
