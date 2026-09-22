"""
Random Strategy for Mastermind.

Filters candidates based on feedback, then picks randomly from remaining.
Serves as a baseline for comparison with information-theoretic strategies.
"""

import random
from typing import List, Tuple


class MastermindRandomStrategy:
    def __init__(self, num_pegs: int = 4):
        self.num_pegs = num_pegs

    def update_belief(self, candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        """Filter candidates based on feedback consistency."""
        return [code for code in candidates if self._is_consistent(code, guess, feedback)]

    def select_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """Select a random guess from remaining candidates."""
        return random.choice(candidates) if candidates else None

    def _is_consistent(self, code: str, guess: str, feedback: Tuple[int, int]) -> bool:
        """Check if a code is consistent with the feedback from a guess."""
        return self._generate_feedback(code, guess) == feedback

    def _generate_feedback(self, target: str, guess: str) -> Tuple[int, int]:
        """Generate (black, white) feedback for a guess against a target."""
        black_pegs = 0
        white_pegs = 0

        target_chars = list(target)
        guess_chars = list(guess)

        for i in range(self.num_pegs):
            if guess_chars[i] == target_chars[i]:
                black_pegs += 1
                target_chars[i] = None
                guess_chars[i] = None

        for i in range(self.num_pegs):
            if guess_chars[i] is not None and guess_chars[i] in target_chars:
                white_pegs += 1
                target_chars[target_chars.index(guess_chars[i])] = None

        return (black_pegs, white_pegs)
