"""GameEngine: the state machine that drives one room's game.

LOBBY -> CHOOSING (drawer picks a word) -> DRAWING (timer, hints, guesses)
      -> TURN_END (word revealed, scores) -> next turn ... -> GAME_OVER
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from enum import Enum
from typing import TYPE_CHECKING

from app.game.canvas import Canvas
from app.game.errors import GameError
from app.game.player import Player
from app.game.scoring import ScoreCalculator
from app.game.words import HintGenerator, MatchResult, WordBank, WordMatcher
from app.schemas.game import ServerEvent as E
from app.schemas.room import WordMode

if TYPE_CHECKING:
    from app.game.room import Room

log = logging.getLogger(__name__)


class Phase(str, Enum):
    LOBBY = "lobby"
    CHOOSING = "choosing_word"
    DRAWING = "drawing"
    TURN_END = "turn_end"
    GAME_OVER = "game_over"


class GameEngine:
    CHOOSE_TIME = 15       # seconds the drawer has to pick a word
    TURN_END_DELAY = 5     # seconds the word/scores stay on screen
    MIN_PLAYERS = 2
    MAX_TEXT = 200

    def __init__(self, room: "Room", words: WordBank | None = None,
                 scoring: ScoreCalculator | None = None, matcher: WordMatcher | None = None) -> None:
        self.room = room
        self.words = words or WordBank.default()
        self.scoring = scoring or ScoreCalculator()
        self.matcher = matcher or WordMatcher()
        self.canvas = Canvas()
        self._task: asyncio.Task | None = None
        self._reset()

    # ------------------------------------------------------------------ state
    def _reset(self) -> None:
        self.phase = Phase.LOBBY
        self.round_no = 0
        self.drawer_id: str | None = None
        self.word: str | None = None
        self.word_options: list[str] = []
        self.used_words: set[str] = set()
        self.revealed: set[int] = set()
        self.guess_order: list[str] = []
        self.turn_queue: list[str] = []
        self.turn_ends_at = 0.0
        self._hint_times: list[float] = []
        self.canvas.clear()

    @property
    def time_left(self) -> int:
        if self.phase not in (Phase.CHOOSING, Phase.DRAWING):
            return 0
        return max(0, math.ceil(self.turn_ends_at - time.monotonic()))

    @property
    def hint(self) -> str | None:
        if self.phase != Phase.DRAWING or self.word is None:
            return None
        if self.room.settings.word_mode == WordMode.HIDDEN:
            return None
        return HintGenerator.mask(self.word, self.revealed)

    @property
    def drawer(self) -> Player | None:
        return self.room.players.get(self.drawer_id) if self.drawer_id else None

    # ------------------------------------------------------------- task utils
    def _cancel(self) -> None:
        if self._task and self._task is not asyncio.current_task():
            self._task.cancel()
        self._task = None

    def _schedule(self, coro) -> None:
        self._cancel()
        task = asyncio.create_task(coro)
        task.add_done_callback(self._on_task_done)
        self._task = task

    @staticmethod
    def _on_task_done(task: asyncio.Task) -> None:
        if not task.cancelled() and task.exception():
            log.error("engine task crashed", exc_info=task.exception())

    def shutdown(self) -> None:
        self._cancel()

    # ------------------------------------------------------------ game flow
    async def start_game(self, requester: Player) -> None:
        room = self.room
        if requester.id != room.host_id:
            raise GameError("Only the host can start the game")
        if self.phase not in (Phase.LOBBY, Phase.GAME_OVER):
            raise GameError("Game already in progress")
        if len(room.connected_players()) < self.MIN_PLAYERS:
            raise GameError(f"Need at least {self.MIN_PLAYERS} players")
        self._cancel()
        self._reset()
        for pid in [p.id for p in room.players.values() if not p.connected]:
            del room.players[pid]
        for p in room.players.values():
            p.reset_for_game()
        await room.broadcast(E.GAME_STARTED, {
            "rounds": room.settings.rounds, "players": room.players_payload()})
        await self._next_turn()

    async def _next_turn(self) -> None:
        room = self.room
        if len(room.connected_players()) < self.MIN_PLAYERS:
            await self._finish("not_enough_players")
            return
        drawer = None
        while drawer is None:
            if not self.turn_queue:
                if self.round_no >= room.settings.rounds:
                    await self._finish("completed")
                    return
                self.round_no += 1
                self.turn_queue = [p.id for p in room.connected_players()]
            candidate = room.players.get(self.turn_queue.pop(0))
            if candidate and candidate.connected:
                drawer = candidate
        await self._begin_choosing(drawer)

    async def _begin_choosing(self, drawer: Player) -> None:
        room = self.room
        self.phase = Phase.CHOOSING
        self.drawer_id = drawer.id
        self.word = None
        self.revealed = set()
        self.guess_order = []
        self.canvas.clear()
        for p in room.players.values():
            p.reset_for_turn()
        self.word_options = self.words.pick_options(room.settings, self.used_words)
        self.turn_ends_at = time.monotonic() + self.CHOOSE_TIME
        await room.broadcast(E.ROUND_START, {
            "round": self.round_no, "total_rounds": room.settings.rounds,
            "drawer_id": drawer.id, "drawer_name": drawer.name,
            "choose_time": self.CHOOSE_TIME, "draw_time": room.settings.draw_time,
            "players": room.players_payload()})
        await room.send(drawer.id, E.WORD_OPTIONS, {
            "options": self.word_options, "choose_time": self.CHOOSE_TIME})
        self._schedule(self._choose_timeout())

    async def _choose_timeout(self) -> None:
        await asyncio.sleep(self.CHOOSE_TIME)
        if self.phase == Phase.CHOOSING and self.word_options:
            import random
            await self._start_drawing(random.choice(self.word_options))

    async def choose_word(self, player: Player, choice) -> None:
        if self.phase != Phase.CHOOSING or player.id != self.drawer_id:
            raise GameError("You can't choose a word right now")
        word = None
        if isinstance(choice, int) and not isinstance(choice, bool) and 0 <= choice < len(self.word_options):
            word = self.word_options[choice]
        elif isinstance(choice, str):
            word = next((w for w in self.word_options if w == choice.strip().lower()), None)
        if word is None:
            raise GameError("Pick one of the offered words")
        await self._start_drawing(word)

    async def _start_drawing(self, word: str) -> None:
        room, s = self.room, self.room.settings
        self.word = word
        self.used_words.add(word)
        self.phase = Phase.DRAWING
        self.revealed = set()
        self.guess_order = []
        self.turn_ends_at = time.monotonic() + s.draw_time
        hidden = s.word_mode == WordMode.HIDDEN
        self._hint_times = [] if hidden else HintGenerator.schedule(s.draw_time, s.hints)
        payload = {"drawer_id": self.drawer_id, "draw_time": s.draw_time, "hint": self.hint}
        await room.broadcast(E.DRAWING_START, payload, exclude={self.drawer_id})
        await room.send(self.drawer_id, E.DRAWING_START, {**payload, "word": word})
        self._schedule(self._run_turn())

    async def _run_turn(self) -> None:
        room, s = self.room, self.room.settings
        next_hint = 0
        while True:
            left = self.turn_ends_at - time.monotonic()
            if left <= 0:
                break
            elapsed = s.draw_time - left
            while next_hint < len(self._hint_times) and elapsed >= self._hint_times[next_hint]:
                if HintGenerator.reveal_next(self.word, self.revealed):
                    await room.broadcast(E.HINT, {"hint": self.hint}, exclude={self.drawer_id})
                next_hint += 1
            await room.broadcast(E.TIMER, {"time_left": math.ceil(left)})
            await asyncio.sleep(min(1.0, left))
        await self._end_turn("time_up")

    async def _end_turn(self, reason: str) -> None:
        if self.phase not in (Phase.CHOOSING, Phase.DRAWING):
            return
        room = self.room
        word = self.word
        drawer = self.drawer
        guessers = [p for p in room.connected_players() if p.id != self.drawer_id]
        drawer_points = 0
        if drawer and word:
            drawer_points = self.scoring.drawer_points(len(self.guess_order), len(guessers))
            drawer.add_score(drawer_points)
            drawer.turn_points = drawer_points
        self.phase = Phase.TURN_END
        await room.broadcast(E.ROUND_END, {
            "word": word, "reason": reason, "round": self.round_no,
            "drawer_id": self.drawer_id, "drawer_points": drawer_points,
            "players": room.players_payload()})
        self._schedule(self._pause_then_next())

    async def _pause_then_next(self) -> None:
        await asyncio.sleep(self.TURN_END_DELAY)
        await self._next_turn()

    async def _finish(self, reason: str) -> None:
        self._cancel()
        self.phase = Phase.GAME_OVER
        self.word = None
        self.drawer_id = None
        board = self.leaderboard()
        winners = [e for e in board if e["rank"] == 1]
        await self.room.broadcast(E.GAME_OVER, {
            "winner": winners[0] if winners else None, "winners": winners,
            "leaderboard": board, "reason": reason})
        await self.room.game_finished(board)

    def leaderboard(self) -> list[dict]:
        ordered = sorted(self.room.players.values(), key=lambda p: p.score, reverse=True)
        board, rank, last = [], 0, None
        for i, p in enumerate(ordered, 1):
            if p.score != last:
                rank, last = i, p.score
            board.append({"rank": rank, "player_id": p.id, "name": p.name,
                          "score": p.score, "connected": p.connected})
        return board

    async def on_player_left(self, player: Player) -> None:
        if self.phase not in (Phase.CHOOSING, Phase.DRAWING):
            return
        if player.id == self.drawer_id:
            await self._end_turn("drawer_left")
        elif len(self.room.connected_players()) < self.MIN_PLAYERS:
            await self._finish("not_enough_players")
        elif self.phase == Phase.DRAWING:
            await self._check_all_guessed()

    # ------------------------------------------------------ guessing & chat
    async def handle_text(self, player: Player, text: str) -> None:
        """Single entry point for `guess` and `chat`: decides if a message is a guess."""
        room = self.room
        text = (text or "").strip()[: self.MAX_TEXT]
        if not text:
            return
        in_round = self.phase == Phase.DRAWING and self.word is not None
        is_drawer = player.id == self.drawer_id

        if in_round and not is_drawer and not player.has_guessed:
            result = self.matcher.check(text, self.word)
            if result == MatchResult.CORRECT:
                await self._award_guess(player)
            elif result == MatchResult.CLOSE:
                await room.send(player.id, E.CLOSE_GUESS, {"text": text})
            else:
                await room.broadcast(E.CHAT_MESSAGE, self._chat(player, text, "guess"))
            return

        if in_round:  # drawer / already-correct players: private channel, never leak the word
            if self.matcher.check(text, self.word) != MatchResult.WRONG:
                raise GameError("You can't reveal the word")
            allowed = [p.id for p in room.players.values() if p.has_guessed]
            allowed.append(self.drawer_id)
            await room.send_many(allowed, E.CHAT_MESSAGE, self._chat(player, text, "chat"))
            return

        await room.broadcast(E.CHAT_MESSAGE, self._chat(player, text, "chat"))

    @staticmethod
    def _chat(player: Player, text: str, kind: str) -> dict:
        return {"kind": kind, "player_id": player.id, "player_name": player.name, "text": text}

    async def _award_guess(self, player: Player) -> None:
        rank = len(self.guess_order)
        points = self.scoring.guesser_points(self.time_left, self.room.settings.draw_time, rank)
        player.has_guessed = True
        player.turn_points = points
        player.add_score(points)
        self.guess_order.append(player.id)
        await self.room.broadcast(E.GUESS_RESULT, {
            "correct": True, "player_id": player.id, "player_name": player.name,
            "points": points, "players": self.room.players_payload()})
        await self._check_all_guessed()

    async def _check_all_guessed(self) -> None:
        guessers = [p for p in self.room.connected_players() if p.id != self.drawer_id]
        if guessers and all(p.has_guessed for p in guessers):
            await self._end_turn("all_guessed")

    # -------------------------------------------------------------- drawing
    def _require_drawer(self, player: Player) -> None:
        if self.phase != Phase.DRAWING or player.id != self.drawer_id:
            raise GameError("Only the drawer can draw")

    async def draw_start(self, player: Player, data: dict) -> None:
        self._require_drawer(player)
        stroke = self.canvas.start(data.get("x"), data.get("y"), data.get("color", "#000000"),
                                   data.get("size", 4), data.get("tool", "pen"))
        x, y = stroke.points[0]
        await self.room.broadcast(E.DRAW_DATA, {
            "type": "start", "x": x, "y": y, "color": stroke.color,
            "size": stroke.size, "tool": stroke.tool}, exclude={player.id})

    async def draw_move(self, player: Player, data: dict) -> None:
        self._require_drawer(player)
        raw = data.get("points")
        if raw is None:
            raw = [[data.get("x"), data.get("y")]]
        if not isinstance(raw, list):
            raise GameError("Invalid points")
        accepted = []
        for pt in raw[:50]:
            if not isinstance(pt, (list, tuple)) or len(pt) != 2:
                raise GameError("Invalid points")
            point = self.canvas.add_point(pt[0], pt[1])
            if point:
                accepted.append(point)
        if accepted:
            await self.room.broadcast(E.DRAW_DATA, {"type": "move", "points": accepted},
                                      exclude={player.id})

    async def draw_end(self, player: Player) -> None:
        self._require_drawer(player)
        self.canvas.end()
        await self.room.broadcast(E.DRAW_DATA, {"type": "end"}, exclude={player.id})

    async def clear_canvas(self, player: Player) -> None:
        self._require_drawer(player)
        self.canvas.clear()
        await self.room.broadcast(E.CANVAS_CLEAR, {})

    async def undo(self, player: Player) -> None:
        self._require_drawer(player)
        self.canvas.undo()
        await self.room.broadcast(E.DRAW_UNDO, {"strokes": self.canvas.to_list()})
