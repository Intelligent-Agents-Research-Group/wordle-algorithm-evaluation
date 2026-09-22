"""
CSS Strategy for Mastermind.

Uses minimax regret: selects guesses that minimize the worst-case
(maximum) number of remaining candidates after receiving feedback.
Works with both Classic (6 colors) and Extended (8 colors) variants.
"""

from typing import List, Tuple
import random


class MastermindCSSStrategy:
    """
    Min-Max Regret Strategy for Mastermind.

    Selects guesses that minimize the worst-case (maximum) number of
    remaining candidates, regardless of what the target code turns out to be.

    This provides a performance guarantee: after each guess, the remaining
    candidate set will be no larger than a certain size, even in the worst case.
    """

    def __init__(self, num_pegs: int = 4):
        self.num_pegs = num_pegs
        self.knowledge_base = {}
        self.attempt_penalty = -1.0
        self.success_reward = 10.0

    def set_rewards(self, attempt_penalty: float, success_reward: float):
        """Set the reward parameters for the strategy."""
        self.attempt_penalty = attempt_penalty
        self.success_reward = success_reward

    def update_belief(self, candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        """Update belief and filter candidates based on feedback."""
        self.knowledge_base[guess] = feedback
        return [code for code in candidates if self._is_consistent(code, guess, feedback)]

    def select_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """
        Select the next guess using min-max regret principle.

        For each potential guess, compute the worst-case (maximum) number of
        candidates that could remain after receiving feedback. Select the
        guess that minimizes this worst-case outcome.
        """
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # If only 2 candidates, just pick one (both have same worst-case of 1)
        if len(candidates) == 2:
            return candidates[0]

        # Sample candidates for efficiency on large candidate sets
        sample_size = min(len(candidates), 100)
        sample_candidates = random.sample(candidates, sample_size)

        best_guess = None
        best_worst_case = float('inf')  # We want to MINIMIZE the worst case

        for guess in sample_candidates:
            # Calculate worst-case remaining candidates for this guess
            worst_case = self._calculate_worst_case(guess, sample_candidates)

            # Select guess with minimum worst-case
            if worst_case < best_worst_case:
                best_worst_case = worst_case
                best_guess = guess
            # Tie-breaker: prefer guesses that are themselves candidates
            elif worst_case == best_worst_case and guess in candidates:
                best_guess = guess

        return best_guess

    def _calculate_worst_case(self, guess: str, candidates: List[str]) -> int:
        """
        Calculate the worst-case (maximum) number of remaining candidates
        for a given guess across all possible feedback patterns.

        This is the core of min-max regret: we find the feedback pattern
        that would leave the MOST candidates, representing our worst-case scenario.
        """
        feedback_groups = {}

        for candidate in candidates:
            feedback = self._generate_feedback(candidate, guess)
            if feedback not in feedback_groups:
                feedback_groups[feedback] = 0
            feedback_groups[feedback] += 1

        # Return the maximum group size (worst case)
        if not feedback_groups:
            return 0
        return max(feedback_groups.values())

    def _is_consistent(self, code: str, guess: str, feedback: Tuple[int, int]) -> bool:
        """Check if a code is consistent with the feedback from a guess."""
        return self._generate_feedback(code, guess) == feedback

    def _generate_feedback(self, target: str, guess: str) -> Tuple[int, int]:
        """Generate (black, white) feedback for a guess against a target."""
        black_pegs = 0
        white_pegs = 0

        target_chars = list(target)
        guess_chars = list(guess)

        # Count black pegs
        for i in range(self.num_pegs):
            if guess_chars[i] == target_chars[i]:
                black_pegs += 1
                target_chars[i] = None
                guess_chars[i] = None

        # Count white pegs
        for i in range(self.num_pegs):
            if guess_chars[i] is not None and guess_chars[i] in target_chars:
                white_pegs += 1
                target_chars[target_chars.index(guess_chars[i])] = None

        return (black_pegs, white_pegs)

    def score_candidates(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]], top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Score and rank candidates, returning top-k (code, score) pairs.

        For minmax, lower worst-case is better, so we negate for scoring
        (higher score = better guess).
        """
        if not candidates:
            return []
        if len(candidates) <= top_k:
            return [(c, 1.0) for c in candidates]

        sample_size = min(len(candidates), 100)
        sample_candidates = random.sample(candidates, sample_size)

        scored = []
        for guess in sample_candidates:
            worst_case = self._calculate_worst_case(guess, sample_candidates)
            # Negate so that lower worst-case = higher score
            score = -worst_case
            # Bonus for being a candidate (could win immediately)
            if guess in candidates:
                score += 0.5
            scored.append((guess, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
