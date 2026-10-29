"""Server-side canvas model: stores validated strokes so late joiners can replay them."""
import math
import re
from dataclasses import dataclass, field

from app.game.errors import GameError

_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


@dataclass
class Stroke:
    color: str
    size: int
    tool: str
    points: list[list[float]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"color": self.color, "size": self.size, "tool": self.tool, "points": self.points}


class Canvas:
    """Coordinates are normalised to 0..1 so clients with different canvas sizes agree."""

    MAX_STROKES = 500
    MAX_POINTS_PER_STROKE = 5000
    TOOLS = {"pen", "eraser"}

    def __init__(self) -> None:
        self._strokes: list[Stroke] = []
        self._active: Stroke | None = None

    @staticmethod
    def _coord(value) -> float:
        try:
            v = float(value)
        except (TypeError, ValueError):
            raise GameError("Invalid coordinates")
        if not math.isfinite(v):
            raise GameError("Invalid coordinates")
        return round(min(1.0, max(0.0, v)), 4)

    def start(self, x, y, color="#000000", size=4, tool="pen") -> Stroke:
        if not isinstance(color, str) or not _COLOR_RE.match(color):
            raise GameError("Invalid color")
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= 50:
            raise GameError("Invalid brush size")
        if tool not in self.TOOLS:
            raise GameError("Invalid tool")
        if len(self._strokes) >= self.MAX_STROKES:
            raise GameError("Canvas is full - undo or clear")
        stroke = Stroke(color, size, tool, [[self._coord(x), self._coord(y)]])
        self._strokes.append(stroke)
        self._active = stroke
        return stroke

    def add_point(self, x, y) -> list[float] | None:
        if self._active is None or len(self._active.points) >= self.MAX_POINTS_PER_STROKE:
            return None
        point = [self._coord(x), self._coord(y)]
        self._active.points.append(point)
        return point

    def end(self) -> None:
        self._active = None

    def undo(self) -> bool:
        self._active = None
        if self._strokes:
            self._strokes.pop()
            return True
        return False

    def clear(self) -> None:
        self._strokes.clear()
        self._active = None

    def to_list(self) -> list[dict]:
        return [s.to_dict() for s in self._strokes]
