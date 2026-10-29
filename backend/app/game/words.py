"""Word list, hint generation and guess matching."""
import json
import random
import re
import unicodedata
from enum import Enum
from pathlib import Path

from app.config import WORDS_PATH
from app.schemas.room import RoomSettings, WordMode


class MatchResult(str, Enum):
    WRONG = "wrong"
    CLOSE = "close"
    CORRECT = "correct"


class WordMatcher:
    """Case-insensitive, trimmed, accent/space/hyphen-tolerant matching.

    CORRECT : same word after normalisation ("Ice-Cream " == "ice cream" == "icecream")
    CLOSE   : one typo away, or the guess merely contains the word (partial) - never scores
    """

    @staticmethod
    def normalize(text: str) -> str:
        text = unicodedata.normalize("NFKD", text)
        text = "".join(c for c in text if not unicodedata.combining(c))
        return re.sub(r"[\s\-_]+", " ", text.strip().casefold())

    @classmethod
    def _compact(cls, text: str) -> str:
        return cls.normalize(text).replace(" ", "")

    @staticmethod
    def _within_one_edit(a: str, b: str) -> bool:
        if abs(len(a) - len(b)) > 1:
            return False
        if len(a) > len(b):
            a, b = b, a
        i = j = edits = 0
        while i < len(a) and j < len(b):
            if a[i] == b[j]:
                i += 1
                j += 1
                continue
            edits += 1
            if edits > 1:
                return False
            if len(a) == len(b):
                i += 1
            j += 1
        return edits + (len(b) - j) <= 1

    def check(self, guess: str, word: str) -> MatchResult:
        g, w = self._compact(guess), self._compact(word)
        if not g or not w:
            return MatchResult.WRONG
        if g == w:
            return MatchResult.CORRECT
        if len(w) >= 4 and self._within_one_edit(g, w):
            return MatchResult.CLOSE
        if len(w) >= 3 and w in g:
            return MatchResult.CLOSE
        return MatchResult.WRONG


class HintGenerator:
    """Builds masked hints like '_ _ a _ _' and decides when letters are revealed."""

    @staticmethod
    def mask(word: str, revealed: set[int]) -> str:
        chars = [c if (i in revealed or not c.isalnum()) else "_" for i, c in enumerate(word)]
        return " ".join(chars)

    @staticmethod
    def schedule(draw_time: int, hints: int) -> list[float]:
        return [draw_time * k / (hints + 1) for k in range(1, hints + 1)]

    @staticmethod
    def reveal_next(word: str, revealed: set[int]) -> bool:
        letters = [i for i, c in enumerate(word) if c.isalnum()]
        if len(revealed) >= len(letters) // 2:  # always keep at least half hidden
            return False
        candidates = [i for i in letters if i not in revealed]
        if not candidates:
            return False
        revealed.add(random.choice(candidates))
        return True


class WordBank:
    """Categorised word list loaded from JSON, plus host custom words."""

    _default: "WordBank | None" = None

    def __init__(self, path: Path = WORDS_PATH) -> None:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        self._categories = {k: [w.lower() for w in v] for k, v in raw.items()}

    @classmethod
    def default(cls) -> "WordBank":
        if cls._default is None:
            cls._default = cls()
        return cls._default

    @property
    def categories(self) -> list[str]:
        return list(self._categories)

    def _pool(self, settings: RoomSettings) -> list[str]:
        if settings.category in self._categories:
            base = self._categories[settings.category]
        else:
            base = [w for words in self._categories.values() for w in words]
        return list(dict.fromkeys(base + settings.custom_words))

    def pick_options(self, settings: RoomSettings, used: set[str]) -> list[str]:
        pool = self._pool(settings)
        fresh = [w for w in pool if w not in used] or pool
        count = settings.word_count
        if settings.word_mode == WordMode.COMBINATION and len(pool) >= 2:
            options: list[str] = []
            for _ in range(count * 5):
                phrase = " ".join(random.sample(pool, 2))
                if phrase not in options:
                    options.append(phrase)
                if len(options) == count:
                    break
            return options
        return random.sample(fresh, min(count, len(fresh)))
