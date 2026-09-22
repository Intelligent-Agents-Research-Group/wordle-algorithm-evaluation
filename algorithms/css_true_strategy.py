"""
True Current Solution Strategy (CSS) for Wordle.

Based on Lu & Boutilier (IJCAI 2011) "Robust Approximation and Incremental
Elicitation in Voting Protocols".

The key insight from the paper: CSS generates queries by considering the
current solution to the minimax optimization—i.e., the minimax optimal
alternative and adversarial witness—and using this to choose queries with
greatest potential to reduce minimax regret.

Adapted for Wordle:
- The "current solution" is a candidate word we're considering
- The "adversarial witness" is the worst-case feedback pattern that would
  leave the most candidates remaining
- CSS selects guesses that specifically target reducing this worst-case gap,
  rather than just maximizing expected information gain

This differs from pure minimax in that it's more targeted: it identifies
the specific adversarial witness and selects guesses that directly attack
that witness's advantage.
"""

from typing import List, Tuple, Dict
import random
from collections import defaultdict


class CSSTrueStrategy:
    """
    True Current Solution Strategy based on minimax regret with
    adversarial witness targeting.

    The algorithm:
    1. For each candidate guess, identify the worst-case feedback pattern
       (adversarial witness) - the one leaving most candidates
    2. Calculate the "regret" for each guess as the worst-case remaining candidates
    3. Select the guess that minimizes this worst-case regret
    4. Additionally: when ties occur, prefer guesses that better discriminate
       among the worst-case candidate group (targeting the witness)
    """

    def __init__(self, verbose: bool = False):
        self.knowledge_base = {}
        self.attempt_penalty = -1.0
        self.success_reward = 10.0
        self.verbose = verbose

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
        Select the next guess using true CSS (minimax regret with witness targeting).

        The strategy:
        1. Find the minimax optimal guess and its adversarial witness
        2. Among guesses with similar minimax performance, prefer those that
           better discriminate the worst-case candidate group
        """
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        if len(candidates) == 2:
            return candidates[0]

        # Sample candidates for efficiency on large candidate sets
        sample_size = min(len(candidates), 100)
        sample_candidates = random.sample(candidates, sample_size)

        # Phase 1: Find minimax regret for each guess and identify adversarial witnesses
        guess_analysis = []

        for guess in sample_candidates:
            feedback_groups = self._get_feedback_groups(guess, sample_candidates)

            # Find the adversarial witness (worst-case feedback pattern)
            worst_feedback = max(feedback_groups.keys(), key=lambda f: len(feedback_groups[f]))
            worst_case_size = len(feedback_groups[worst_feedback])
            worst_case_candidates = feedback_groups[worst_feedback]

            guess_analysis.append({
                'guess': guess,
                'worst_case_size': worst_case_size,
                'worst_feedback': worst_feedback,
                'worst_case_candidates': worst_case_candidates,
                'feedback_groups': feedback_groups,
                'num_groups': len(feedback_groups)
            })

        # Phase 2: Find minimum worst-case size (minimax regret)
        min_worst_case = min(g['worst_case_size'] for g in guess_analysis)

        # Get all guesses that achieve the minimax optimal
        minimax_optimal_guesses = [g for g in guess_analysis if g['worst_case_size'] == min_worst_case]

        if self.verbose:
            print(f"  [CSS] {len(minimax_optimal_guesses)} guesses achieve minimax optimal "
                  f"(worst-case: {min_worst_case} candidates)")

        # Phase 3: Among minimax-optimal guesses, apply witness targeting
        # Prefer guesses that better discriminate among the worst-case candidates
        best_guess = None
        best_score = float('-inf')

        for g in minimax_optimal_guesses:
            # Score based on how well this guess discriminates the worst-case group
            # This is the "targeting the witness" aspect of CSS

            # Primary: minimize worst case (already satisfied by being in this list)
            # Secondary: maximize discrimination of the worst-case candidates
            # Tertiary: prefer more feedback groups (better overall discrimination)

            witness_discrimination = self._calculate_witness_discrimination(
                g['guess'],
                g['worst_case_candidates'],
                sample_candidates
            )

            # Combined score: witness discrimination + tie-breaker for more groups
            score = witness_discrimination + 0.01 * g['num_groups']

            # Bonus for being a candidate (can win immediately)
            if g['guess'] in candidates:
                score += 0.001

            if score > best_score:
                best_score = score
                best_guess = g['guess']

        if self.verbose:
            print(f"  [CSS] Selected '{best_guess}' with witness discrimination score: {best_score:.4f}")

        return best_guess

    def _calculate_witness_discrimination(self, guess: str, worst_case_candidates: List[str],
                                          all_candidates: List[str]) -> float:
        """
        Calculate how well a guess discriminates among the worst-case candidates.

        This implements the "targeting the witness" aspect of CSS:
        We want guesses that, even in the worst case, would help us
        distinguish between the remaining candidates in subsequent rounds.

        Higher score = better discrimination of the adversarial witness group.
        """
        if len(worst_case_candidates) <= 1:
            return 1.0  # Perfect discrimination if only 0-1 candidates

        # Look at how this guess would partition the worst-case candidates
        # if we were to ask it as a follow-up
        sub_groups = defaultdict(list)
        for candidate in worst_case_candidates:
            feedback = tuple(self._generate_feedback(candidate, guess))
            sub_groups[feedback].append(candidate)

        # More sub-groups = better discrimination of the witness
        num_sub_groups = len(sub_groups)

        # Also consider evenness of the split (entropy-like measure)
        total = len(worst_case_candidates)
        evenness = 0
        for group in sub_groups.values():
            p = len(group) / total
            if p > 0:
                evenness -= p * (1 - p)  # Gini-like measure, higher when more even

        # Normalize by maximum possible groups
        max_possible_groups = min(len(worst_case_candidates), 243)  # 3^5 possible feedback patterns

        score = (num_sub_groups / max_possible_groups) + evenness
        return score

    def _get_feedback_groups(self, guess: str, candidates: List[str]) -> Dict[tuple, List[str]]:
        """Group candidates by the feedback they would produce for a given guess."""
        groups = defaultdict(list)
        for candidate in candidates:
            feedback = tuple(self._generate_feedback(candidate, guess))
            groups[feedback].append(candidate)
        return dict(groups)

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


class CSSTrueWithExploitationStrategy(CSSTrueStrategy):
    """
    True CSS with late-game exploitation.

    Uses CSS for most of the game, but switches to exploitation
    when few candidates remain or when running low on attempts.
    """

    def __init__(self, exploitation_threshold: int = 3, verbose: bool = False):
        super().__init__(verbose=verbose)
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
            return candidates[0]

        # If very few candidates, exploit rather than explore
        if len(candidates) <= self.exploitation_threshold:
            return candidates[0]

        # Otherwise, use CSS strategy
        return super().select_guess(candidates, history)
