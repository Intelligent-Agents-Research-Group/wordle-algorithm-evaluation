from typing import List, Tuple
import random

class MinMaxStrategy:
    """
    Min-Max Regret Strategy for Wordle.

    Selects guesses that minimize the worst-case (maximum) number of
    remaining candidates, regardless of what the target word turns out to be.

    This provides a performance guarantee: after each guess, the remaining
    candidate set will be no larger than a certain size, even in the worst case.
    """

    def __init__(self):
        self.knowledge_base = {}
        self.attempt_penalty = -1.0
        self.success_reward = 10.0

    def set_rewards(self, attempt_penalty: float, success_reward: float):
        """Set the reward parameters for the strategy."""
        self.attempt_penalty = attempt_penalty
        self.success_reward = success_reward

    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update belief and filter candidates based on feedback."""
        self.knowledge_base[guess] = feedback
        return [word for word in candidates if self._is_consistent(word, guess, feedback)]

    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
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
        guesses_to_evaluate = sample_candidates

        best_guess = None
        best_worst_case = float('inf')  # We want to MINIMIZE the worst case

        for guess in guesses_to_evaluate:
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
            feedback = tuple(self._generate_feedback(candidate, guess))
            if feedback not in feedback_groups:
                feedback_groups[feedback] = 0
            feedback_groups[feedback] += 1

        # Return the maximum group size (worst case)
        if not feedback_groups:
            return 0
        return max(feedback_groups.values())

    def _is_consistent(self, word: str, guess: str, feedback: List[str]) -> bool:
        """Check if a word is consistent with the feedback from a guess."""
        expected_feedback = self._generate_feedback(word, guess)
        return expected_feedback == feedback

    def _generate_feedback(self, target: str, guess: str) -> List[str]:
        """Generate feedback for a guess against a target word."""
        feedback = ["-"] * 5
        target_chars = list(target)
        guess_chars = list(guess)

        # Mark greens (correct position)
        for i in range(5):
            if guess_chars[i] == target_chars[i]:
                feedback[i] = "G"
                target_chars[i] = None
                guess_chars[i] = None

        # Mark yellows (wrong position)
        for i in range(5):
            if guess_chars[i] and guess_chars[i] in target_chars:
                feedback[i] = "Y"
                target_chars[target_chars.index(guess_chars[i])] = None

        return feedback


class MinMaxWithExploitationStrategy(MinMaxStrategy):
    """
    Min-Max strategy with late-game exploitation.

    Uses min-max regret for most of the game, but switches to
    exploitation (guessing from candidates) when few candidates remain
    or when running low on attempts.
    """

    def __init__(self, exploitation_threshold: int = 3):
        super().__init__()
        self.exploitation_threshold = exploitation_threshold

    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Select guess with adaptive exploitation in late game."""
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        attempts_remaining = 6 - len(history)

        # Late game: if candidates <= attempts remaining, exploit
        if len(candidates) <= attempts_remaining:
            # Just pick a candidate (guaranteed to win)
            return candidates[0]

        # If very few candidates, exploit rather than explore
        if len(candidates) <= self.exploitation_threshold:
            return candidates[0]

        # Otherwise, use min-max strategy
        return super().select_guess(candidates, history)
