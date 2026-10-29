"""Pydantic models describing room settings and REST payloads."""
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class WordMode(str, Enum):
    NORMAL = "normal"            # guessers see blanks (_ _ a _ _)
    HIDDEN = "hidden"            # guessers see nothing about the word
    COMBINATION = "combination"  # word is a combination of two words


class RoomSettings(BaseModel):
    max_players: int = Field(8, ge=2, le=20)
    rounds: int = Field(3, ge=2, le=10)
    draw_time: int = Field(80, ge=15, le=240)
    word_count: int = Field(3, ge=1, le=5)
    hints: int = Field(2, ge=0, le=5)  # 0 = hints disabled
    word_mode: WordMode = WordMode.NORMAL
    is_private: bool = True
    category: str | None = None
    custom_words: list[str] = Field(default_factory=list, max_length=200)

    @field_validator("custom_words")
    @classmethod
    def _clean_words(cls, words: list[str]) -> list[str]:
        cleaned: list[str] = []
        for w in words:
            w = " ".join(w.strip().lower().split())
            if 1 <= len(w) <= 30 and w not in cleaned:
                cleaned.append(w)
        return cleaned


class CreateRoomRequest(BaseModel):
    settings: RoomSettings = Field(default_factory=RoomSettings)


class CreateRoomResponse(BaseModel):
    room_id: str
    is_private: bool
    ws_path: str


class RoomInfo(BaseModel):
    room_id: str
    is_private: bool
    phase: str
    player_count: int
    max_players: int
    rounds: int
    draw_time: int
