import asyncio

import pytest

from app.game.canvas import Canvas
from app.game.engine import GameEngine, Phase
from app.game.errors import GameError
from app.game.room import Room
from app.game.scoring import ScoreCalculator
from app.game.words import HintGenerator, MatchResult, WordBank, WordMatcher
from app.schemas.room import RoomSettings, WordMode
from app.websocket.manager import ConnectionManager


# ---------------------------------------------------------------- matching
@pytest.mark.parametrize("guess,expected", [
    ("Elephant", MatchResult.CORRECT),
    ("  elephant  ", MatchResult.CORRECT),
    ("ELEPHANT", MatchResult.CORRECT),
    ("elephent", MatchResult.CLOSE),         # one typo
    ("is it elephant", MatchResult.CLOSE),   # partial
    ("giraffe", MatchResult.WRONG),
    ("", MatchResult.WRONG),
])
def test_matcher(guess, expected):
    assert WordMatcher().check(guess, "elephant") == expected


def test_matcher_ignores_spaces_hyphens_accents():
    m = WordMatcher()
    assert m.check("Ice-Cream", "ice cream") == MatchResult.CORRECT
    assert m.check("icecream", "ice cream") == MatchResult.CORRECT
    assert m.check("café", "cafe") == MatchResult.CORRECT


# ------------------------------------------------------------------- hints
def test_hint_mask_and_reveal_limits():
    assert HintGenerator.mask("hello", set()) == "_ _ _ _ _"
    assert HintGenerator.mask("hello", {1}) == "_ e _ _ _"
    revealed: set[int] = set()
    results = [HintGenerator.reveal_next("hello", revealed) for _ in range(5)]
    assert results == [True, True, False, False, False]  # keeps >= half hidden
    assert HintGenerator.schedule(90, 2) == [30, 60]
    assert HintGenerator.schedule(90, 0) == []


# ----------------------------------------------------------------- scoring
def test_scoring():
    s = ScoreCalculator()
    assert s.guesser_points(80, 80, 0) > s.guesser_points(10, 80, 0)
    assert s.guesser_points(40, 80, 0) > s.guesser_points(40, 80, 3)
    assert s.guesser_points(0, 80, 0) >= 50
    assert s.drawer_points(0, 3) == 0
    assert s.drawer_points(3, 3) == 300


# ------------------------------------------------------------------ canvas
def test_canvas_flow_and_validation():
    c = Canvas()
    c.start(0.1, 0.2, "#ff0000", 5)
    assert c.add_point(2, -1) == [1.0, 0.0]  # clamped
    c.end()
    c.start(0.5, 0.5)
    c.end()
    assert len(c.to_list()) == 2
    assert c.undo() and len(c.to_list()) == 1
    c.clear()
    assert c.to_list() == []
    with pytest.raises(GameError):
        c.start(0, 0, "red", 5)
    with pytest.raises(GameError):
        c.start(0, 0, "#000000", 999)
    with pytest.raises(GameError):
        c.start("abc", 0)


# --------------------------------------------------------------- word bank
def test_word_bank_modes():
    bank = WordBank.default()
    opts = bank.pick_options(RoomSettings(word_count=4), set())
    assert len(opts) == 4 and len(set(opts)) == 4
    combo = bank.pick_options(RoomSettings(word_count=3, word_mode=WordMode.COMBINATION), set())
    assert all(" " in w for w in combo)
    custom = bank.pick_options(RoomSettings(word_count=1, category="nope", custom_words=["Zebra Crossing"]), set())
    assert len(custom) == 1


# ------------------------------------------------------------ engine (async)
def test_engine_full_game(monkeypatch):
    monkeypatch.setattr(GameEngine, "TURN_END_DELAY", 0.05)
    saved = []

    async def on_over(room, board):
        saved.append(board)

    async def scenario():
        room = Room("TEST01", RoomSettings(rounds=2, draw_time=30, word_count=2), ConnectionManager(), on_over)
        a, _ = room.join("Alice")
        b, _ = room.join("Bob")
        eng = room.engine

        with pytest.raises(GameError):
            await eng.start_game(b)  # not the host
        await eng.start_game(a)

        async def wait_phase(phase):
            for _ in range(200):
                if eng.phase == phase:
                    return
                await asyncio.sleep(0.02)
            raise AssertionError(f"never reached {phase}, stuck in {eng.phase}")

        for _ in range(4):  # 2 rounds x 2 players
            await wait_phase(Phase.CHOOSING)
            drawer = eng.drawer
            guesser = b if drawer is a else a
            with pytest.raises(GameError):
                await eng.choose_word(guesser, 0)
            await eng.choose_word(drawer, 0)
            with pytest.raises(GameError):
                await eng.draw_start(guesser, {"x": 0, "y": 0})
            await eng.draw_start(drawer, {"x": 0.1, "y": 0.1, "color": "#000000", "size": 3})
            await eng.draw_end(drawer)
            await eng.handle_text(guesser, "totally wrong")
            assert not guesser.has_guessed
            with pytest.raises(GameError):
                await eng.handle_text(drawer, eng.word)  # drawer can't leak the word
            await eng.handle_text(guesser, eng.word.upper())
            assert guesser.has_guessed and guesser.turn_points > 0
            await wait_phase(Phase.TURN_END)

        await wait_phase(Phase.GAME_OVER)
        eng.shutdown()
        assert a.score > 0 and b.score > 0
        assert len(saved) == 1 and saved[0][0]["rank"] == 1

    asyncio.run(scenario())


def test_engine_requires_two_players():
    async def scenario():
        room = Room("TEST02", RoomSettings(), ConnectionManager())
        a, _ = room.join("Solo")
        with pytest.raises(GameError):
            await room.engine.start_game(a)

    asyncio.run(scenario())


def test_room_name_dedup_ban_and_capacity():
    room = Room("TEST03", RoomSettings(max_players=2), ConnectionManager())
    a, _ = room.join("Sam")
    b, _ = room.join("sam")
    assert b.name == "sam (2)"
    with pytest.raises(GameError):
        room.join("Third")  # full
    room2 = Room("TEST04", RoomSettings(), ConnectionManager())
    room2.banned_names.add("troll")
    with pytest.raises(GameError):
        room2.join("Troll")
