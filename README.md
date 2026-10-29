# Skribbl Clone

A real-time multiplayer drawing and guessing game inspired by [skribbl.io](https://skribbl.io). Players join a room, take turns drawing a secret word, and race to guess it. Built with React, FastAPI and native WebSockets.

![React](https://img.shields.io/badge/React-18-61dafb?logo=react&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178c6?logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-5-646cff?logo=vite&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.1x-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-3-003b57?logo=sqlite&logoColor=white)
![Tests](https://img.shields.io/badge/tests-23%20passing-brightgreen)

**Live demo:** https://skribbl-clone-k8cu.onrender.com/
**API docs:** https://skribbl-clone-api.onrender.com/docs

> The free Render tier sleeps after 15 minutes of inactivity. The first request can take about a minute to wake the server.

---

## Features

**Rooms and lobby**
- Create public or private rooms with a 6-character code and a shareable invite link
- Host-configurable settings: players (2-20), rounds (2-10), draw time (15-240s), words per turn (1-5), hints (0-5), word mode, custom words
- Lobby with player list, ready-up and host-only start
- Public room browser
- Host moderation: kick and ban. Players can start a vote kick

**Gameplay**
- Turn-based rounds where every player draws once per round
- Drawer picks one of N words, with an automatic pick after 15 seconds
- Real-time canvas sync with brush, colors, brush sizes, eraser, undo and clear
- Hints reveal letters over time (`_ _ a _ _`), with Normal, Hidden and Combination word modes
- Timer, live scores, round summary and final leaderboard
- Reconnect support. Refreshing the page puts you back in the game

**Engineering**
- Object-oriented backend with clear separation between transport, rooms, game logic and persistence
- Server-authoritative game state: scoring, word checks and turn order never run in the browser
- Chat that cannot leak the answer, because the drawer and players who already guessed use a private channel
- Finished matches stored in SQLite with a global leaderboard endpoint

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, React Router, Lucide icons |
| Drawing | HTML5 Canvas API with custom stroke capture and rendering |
| Backend | Python 3.10+, FastAPI, Uvicorn, Pydantic |
| Real time | Native WebSockets (browser API on the client, FastAPI on the server) |
| Storage | In-memory game state, SQLite (`sqlite3`) for match history |
| Testing | pytest, httpx, FastAPI TestClient |
| Hosting | Render (web service and static site) |

---

## Architecture

```
Browser (React)                           FastAPI
 Home  --- POST /api/rooms -----------> rooms API --> RoomRegistry
 Room  --- ws /ws/{code} -------------> game_socket --> MessageHandler (one per connection)
   useRoomSocket (GameSocket)                                  |
   gameReducer  -> UI state                          Room: players, host, moderation
   useCanvas    -> draw capture + render                       |
                                                     GameEngine: phases, timers, hints, guesses
                                                     Canvas | ScoreCalculator | WordBank | WordMatcher
                                                               |
                                                     MatchRepository --> SQLite
```

### How the pieces work

- **Drawing sync:** Pointer events become normalised `(x, y)` points in the 0 to 1 range, so clients with different canvas sizes agree. The drawer paints locally right away and sends batched `draw_move` events every 40 ms. The server validates and stores each stroke, then broadcasts `draw_data` to everyone except the drawer. Late joiners receive the full stroke list when they connect. Undo sends the updated stroke list to all clients.
- **Game state:** `GameEngine` is a state machine: `lobby -> choosing_word -> drawing -> turn_end -> ... -> game_over`. It owns the turn queue, timers, hint schedule and scoring. Clients only render what the server sends.
- **Word matching:** `WordMatcher` trims, lowercases, strips accents and ignores spaces and hyphens, so `Ice-Cream`, `ice cream` and `icecream` all match. A guess that is one typo away, or that contains the word, is treated as "close". The player gets a private hint and no points.
- **Scoring:** a correct guess earns 100 to 500 points depending on time left, reduced by 10% per earlier guesser (minimum 50%). The drawer earns up to 300 points based on the share of players who guessed.
- **Connections:** `ConnectionManager` only handles sockets. `Room` handles membership and permissions. `GameEngine` handles rules. This keeps each class testable on its own.

### Backend classes

| Class | File | Responsibility |
|---|---|---|
| `ConnectionManager` | `websocket/manager.py` | Connect, send, broadcast |
| `MessageHandler` | `websocket/handlers.py` | Route client events to actions |
| `RoomRegistry` | `game/registry.py` | Create, find and clean up rooms |
| `Room` | `game/room.py` | Players, host powers, kick/ban/votekick |
| `GameEngine` | `game/engine.py` | Turns, timers, hints, guesses, drawing |
| `Player` | `game/player.py` | Identity, score, per-turn flags |
| `Canvas`, `Stroke` | `game/canvas.py` | Validated stroke storage, undo |
| `ScoreCalculator` | `game/scoring.py` | Point calculation |
| `WordBank`, `WordMatcher`, `HintGenerator` | `game/words.py` | Words, matching, hints |
| `Database`, `MatchRepository` | `database/` | SQLite persistence |

---

## Project structure

```
skribbl-clone/
├── backend/
│   ├── app/
│   │   ├── api/            # REST routes (rooms, leaderboard)
│   │   ├── websocket/      # ConnectionManager, MessageHandler, /ws endpoint
│   │   ├── game/           # Room, Player, GameEngine, Canvas, scoring, words
│   │   ├── database/       # connection, schema, repository
│   │   ├── schemas/        # Pydantic models and event names
│   │   ├── data/words.json
│   │   ├── config.py
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/     # Canvas, DrawingToolbar, ChatPanel, PlayerList, ...
│   │   ├── pages/          # Home, Lobby, Game, Results, Room
│   │   ├── hooks/          # useWebSocket, useCanvas
│   │   ├── services/       # api.ts, websocket.ts
│   │   ├── state/          # gameReducer.ts
│   │   └── types/
│   └── .env.example
├── render.yaml
└── README.md
```

---

## Getting started

### Prerequisites
- Python 3.10 or newer
- Node.js 18 or newer

### 1. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```
Interactive API docs are at http://localhost:8000/docs.

### 2. Frontend
```bash
cd frontend
npm install
npm run dev
```
Open http://localhost:5173. The Vite dev server proxies `/api` and `/ws` to the backend, so no extra configuration is needed.

### 3. Play
Open two browser windows. Create a room in one, then join from the other using the room code or invite link.

### Tests
```bash
cd backend
pytest
```
The suite covers word matching, hints, scoring, canvas validation, a complete multi-round game, REST endpoints and a two-client WebSocket flow.

---

## Configuration

| Variable | Where | Default | Description |
|---|---|---|---|
| `DB_PATH` | backend | `backend/skribbl.db` | SQLite file location |
| `CORS_ORIGINS` | backend | `http://localhost:5173` | Comma-separated allowed frontend origins |
| `ROOM_EMPTY_GRACE` | backend | `60` | Seconds an empty room is kept alive |
| `VITE_API_URL` | frontend | empty | Backend base URL. Leave empty in local dev |

---

## API reference

### REST
| Method | Path | Description |
|---|---|---|
| `POST` | `/api/rooms` | Create a room. Body: `{ "settings": { ... } }` |
| `GET` | `/api/rooms` | List open public rooms |
| `GET` | `/api/rooms/{id}` | Room details |
| `GET` | `/api/leaderboard` | Top players by wins and score |
| `GET` | `/api/leaderboard/matches` | Recent matches |
| `GET` | `/api/health` | Health check |

### WebSocket
Connect to `/ws/{ROOM_CODE}?name=Alice[&player_id=...]`. The first player to connect becomes the host. Pass a saved `player_id` to reconnect. Messages use the envelope `{ "event": "...", "data": { ... } }`.

**Client to server:** `ready`, `update_settings`, `start_game`, `word_chosen`, `draw_start`, `draw_move`, `draw_end`, `canvas_clear`, `draw_undo`, `guess`, `chat`, `kick`, `ban`, `votekick`, `sync`, `ping`

**Server to client:** `joined`, `player_joined`, `player_left`, `players_update`, `settings_updated`, `game_started`, `round_start`, `word_options`, `drawing_start`, `timer`, `hint`, `draw_data`, `canvas_clear`, `draw_undo`, `guess_result`, `close_guess`, `chat_message`, `round_end`, `game_over`, `kicked`, `error`

Full payload details are in [`backend/README.md`](backend/README.md).

---

## Deployment (Render)

Both services deploy from this one repository.

### Backend (Web Service)
| Field | Value |
|---|---|
| Root Directory | `backend` |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
| Env var | `CORS_ORIGINS` = https://skribbl-clone-k8cu.onrender.com/ |

### Frontend (Static Site)
| Field | Value |
|---|---|
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build` |
| Publish Directory | `dist` |
| Env var | `VITE_API_URL` = (https://skribbl-clone-api.onrender.com/docs?) |
| Redirects/Rewrites | Source `/*`, Destination `/index.html`, Action `Rewrite` |

Deploy the backend first, copy its URL into the frontend's `VITE_API_URL`, deploy the frontend, then set the backend's `CORS_ORIGINS` to the frontend URL and redeploy. `render.yaml` describes both services if you prefer a Blueprint deploy.

### Platform notes
- Render supports WebSockets, and the client automatically uses `wss://` over HTTPS.
- Active games live in memory, so run a **single backend instance**. A restart ends games in progress.
- The free plan has an ephemeral disk. Match history resets on redeploy unless you attach a persistent disk and set `DB_PATH=/data/skribbl.db`.
- `VITE_API_URL` is baked in at build time. Changing it requires redeploying the frontend.

---

## Design decisions and trade-offs

- **Native WebSockets over Socket.IO:** fewer dependencies, and the browser API maps directly to FastAPI's WebSocket support.
- **In-memory live state:** keeps real-time logic simple and fast. SQLite is used only for results that must survive restarts.
- **Server-authoritative logic:** clients cannot award themselves points, see the word, or draw out of turn.
- **Normalised coordinates:** strokes render identically on any screen size.

## Roadmap

- Redis pub/sub to support multiple backend instances
- Avatars and spectator mode
- Round replay
- Multiple word-list languages
- Rate limiting for chat and drawing events

## License

MIT. Add a `LICENSE` file before publishing.
