class Player:
    """A participant: identity, score, connection and per-turn state."""

    def __init__(self, player_id: str, name: str, avatar: int = 0) -> None:
        self.id = player_id
        self.name = name
        self.avatar = avatar
        self.score = 0
        self.turn_points = 0
        self.connected = True
        self.ready = False
        self.has_guessed = False
        self.kick_votes: set[str] = set()

    def add_score(self, points: int) -> None:
        self.score += points

    def reset_for_game(self) -> None:
        self.score = 0
        self.turn_points = 0
        self.has_guessed = False
        self.ready = False

    def reset_for_turn(self) -> None:
        self.turn_points = 0
        self.has_guessed = False

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "avatar": self.avatar,
            "score": self.score, "turn_points": self.turn_points,
            "connected": self.connected, "ready": self.ready,
            "has_guessed": self.has_guessed,
        }
