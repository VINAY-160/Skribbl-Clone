# Skribbl Clone - Backend (FastAPI + native WebSockets + SQLite)

## Run
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest                                              # 23 tests
```
Docs: http://localhost:8000/docs

## OOP map
| Class | File | Job |
|---|---|---|
| `ConnectionManager` | websocket/manager.py | sockets only: connect, send, broadcast |
| `MessageHandler` | websocket/handlers.py | one per connection, routes events to actions |
| `RoomRegistry` | game/registry.py | create/find/cleanup rooms, room codes |
| `Room` | game/room.py | players, host powers, kick/ban/votekick, payloads |
| `GameEngine` | game/engine.py | state machine: turns, timers, hints, guesses, drawing |
| `Player` | game/player.py | identity + score + turn flags |
| `Canvas` / `Stroke` | game/canvas.py | validated stroke store (late joiners, undo) |
| `ScoreCalculator` | game/scoring.py | all point maths (server-side only) |
| `WordBank`, `WordMatcher`, `HintGenerator` | game/words.py | words, guess matching, hints |
| `Database`, `MatchRepository` | database/ | SQLite persistence of finished matches |

## REST
- `POST /api/rooms` `{settings:{...}}` -> `{room_id, ws_path}`
- `GET /api/rooms` (open public rooms) / `GET /api/rooms/{id}`
- `GET /api/leaderboard`, `GET /api/leaderboard/matches`, `GET /api/health`

Settings: `max_players 2-20, rounds 2-10, draw_time 15-240, word_count 1-5, hints 0-5 (0=off), word_mode normal|hidden|combination, is_private, category, custom_words[]`

## WebSocket
Connect: `ws://host/ws/{ROOM_CODE}?name=Alice[&player_id=<saved id>]` (first player = host; send saved `player_id` to reconnect).
Envelope both ways: `{"event": "...", "data": {...}}`. Canvas coords are normalised 0..1.

**Client -> server:** `ping, sync, ready{ready}, update_settings{...}, start_game, word_chosen{word|index}, draw_start{x,y,color,size,tool}, draw_move{points:[[x,y],..]} (or x,y), draw_end, canvas_clear, draw_undo, guess{text}, chat{text}, kick{player_id}, ban{player_id}, votekick{player_id}`

**Server -> client:** `joined{player_id,state}, game_state, player_joined, player_left, players_update, settings_updated, game_started, round_start, word_options (drawer only), drawing_start{hint, word (drawer only)}, timer{time_left}, hint{hint}, draw_data{type:start|move|end}, canvas_clear, draw_undo{strokes}, guess_result{correct,player_name,points}, close_guess, chat_message{kind:guess|chat|system}, round_end{word,players}, game_over{winner,leaderboard}, kicked, error{message}`

`draw_data` goes to everyone except the drawer (drawer renders locally). `hint` looks like `_ _ a _ _`; `hint:null` during drawing = hidden mode.

## Notes
- Live games are in memory (lost on restart); only finished matches are stored in SQLite.
- Render: set `DB_PATH` to a persistent disk path, `CORS_ORIGINS` to the frontend URL.
