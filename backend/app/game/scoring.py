class ScoreCalculator:
    """All point maths lives on the server so clients can never award themselves points."""

    def __init__(self, max_guess: int = 500, min_guess: int = 100, max_drawer: int = 300) -> None:
        self.max_guess = max_guess
        self.min_guess = min_guess
        self.max_drawer = max_drawer

    def guesser_points(self, time_left: float, draw_time: int, rank: int) -> int:
        """Faster guess => more points. `rank` is 0 for the first correct guesser."""
        ratio = max(0.0, min(1.0, time_left / draw_time)) if draw_time else 0.0
        base = self.min_guess + (self.max_guess - self.min_guess) * ratio
        order_factor = max(0.5, 1 - 0.1 * rank)
        return round(base * order_factor)

    def drawer_points(self, correct_guessers: int, total_guessers: int) -> int:
        if total_guessers <= 0 or correct_guessers <= 0:
            return 0
        return round(self.max_drawer * correct_guessers / total_guessers)
