"""
VOI (Value of Information) Strategy for Mastermind.

Uses Bayesian belief tracking with exploration/exploitation balance.
Works with both Classic (6 colors) and Extended (8 colors) variants.
"""

import numpy as np
from typing import List, Tuple
import random
from collections import defaultdict, Counter


class MastermindVOIStrategy:
    def __init__(self, num_pegs: int = 4, verbose: bool = False):
        self.num_pegs = num_pegs
        self.verbose = verbose
        self.beliefs = {}
        self.feedback_cache = {}
        self.color_frequencies = {}
        self.position_frequencies = [defaultdict(int) for _ in range(num_pegs)]
        self.attempt_penalty = -1.0
        self.success_reward = 10.0
        self.reward_weight = 0.5
        self.current_attempt = 0

    def initialize_beliefs(self, candidates: List[str]):
        """Initialize beliefs to a uniform distribution."""
        self.beliefs = {}
        self.color_frequencies = Counter()
        self.position_frequencies = [defaultdict(int) for _ in range(self.num_pegs)]

        for code in candidates:
            for i, color in enumerate(code):
                self.color_frequencies[color] += 1
                self.position_frequencies[i][color] += 1

        total_codes = len(candidates)
        for color in self.color_frequencies:
            self.color_frequencies[color] /= total_codes
        for pos_freq in self.position_frequencies:
            for color in pos_freq:
                pos_freq[color] /= total_codes

        for code in candidates:
            self.beliefs[code] = 1.0 / total_codes

    def update_belief(self, candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        """Update beliefs based on feedback and return filtered candidates."""
        if not self.beliefs:
            self.initialize_beliefs(candidates)

        total_prob = 0
        new_beliefs = {}

        filtered_candidates = []
        for code in candidates:
            expected_feedback = self.get_feedback(guess, code)

            if expected_feedback == feedback:
                filtered_candidates.append(code)
                code_score = self.beliefs.get(code, 1.0 / len(candidates))
                new_beliefs[code] = code_score
                total_prob += code_score

        if total_prob > 0:
            for code in filtered_candidates:
                self.beliefs[code] = new_beliefs[code] / total_prob
        else:
            for code in filtered_candidates:
                self.beliefs[code] = 1.0 / len(filtered_candidates) if filtered_candidates else 0

        return filtered_candidates

    def get_feedback(self, guess: str, target: str) -> Tuple[int, int]:
        """Get feedback from cache or calculate it."""
        key = (guess, target)
        if key not in self.feedback_cache:
            self.feedback_cache[key] = self.calculate_feedback(guess, target)
        return self.feedback_cache[key]

    def calculate_feedback(self, guess: str, target: str) -> Tuple[int, int]:
        """Calculate (black, white) feedback."""
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

    def calculate_voi(self, guess: str, candidates: List[str]) -> float:
        """Calculate the Value of Information for a potential guess."""
        if len(candidates) <= 1:
            return 0.0

        feedback_groups = defaultdict(list)
        for target in candidates:
            feedback = self.get_feedback(guess, target)
            feedback_groups[feedback].append(target)

        entropy_before = self.calculate_entropy(candidates)
        expected_entropy_after = 0

        for feedback, group in feedback_groups.items():
            group_prob = sum(self.beliefs.get(code, 0) for code in group)
            if group_prob > 0:
                group_entropy = 0
                for code in group:
                    p = self.beliefs.get(code, 0) / group_prob
                    if p > 0:
                        group_entropy -= p * np.log2(p)
                expected_entropy_after += group_prob * group_entropy

        info_gain = entropy_before - expected_entropy_after

        max_group_size = max(len(group) for group in feedback_groups.values())
        diversity_bonus = -0.1 * (max_group_size / len(candidates))

        return info_gain + diversity_bonus

    def calculate_entropy(self, candidates: List[str]) -> float:
        """Calculate the current entropy of the belief distribution."""
        entropy = 0
        for code in candidates:
            p = self.beliefs.get(code, 0)
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy

    def select_first_guess(self, candidates: List[str]) -> str:
        """Select an optimal first guess based on color patterns."""
        best_guesses = []
        best_score = -float('inf')

        sample_size = min(len(candidates), 500)
        sampled_candidates = random.sample(candidates, sample_size)

        for code in sampled_candidates:
            score = 0
            used_colors = set()

            for i, color in enumerate(code):
                if color not in used_colors:
                    score += self.color_frequencies.get(color, 0) * 3
                    used_colors.add(color)
                score += self.position_frequencies[i].get(color, 0) * 0.5

            # Bonus for diverse colors (more information)
            score += len(used_colors) * 0.3

            if score > best_score:
                best_score = score
                best_guesses = [code]
            elif score == best_score:
                best_guesses.append(code)

        return random.choice(best_guesses) if best_guesses else candidates[0]

    def set_rewards(self, attempt_penalty: float, success_reward: float):
        """Set the reward parameters for the strategy."""
        self.attempt_penalty = attempt_penalty
        self.success_reward = success_reward

    def calculate_expected_reward(self, guess: str, candidates: List[str]) -> float:
        """Calculate the expected reward for a potential guess."""
        if len(candidates) <= 1:
            return self.success_reward + self.attempt_penalty

        feedback_groups = defaultdict(list)
        for target in candidates:
            feedback = self.get_feedback(guess, target)
            feedback_groups[feedback].append(target)

        expected_reward = self.attempt_penalty

        for feedback, group in feedback_groups.items():
            group_prob = sum(self.beliefs.get(code, 0) for code in group)
            if guess in group:
                expected_reward += group_prob * self.success_reward

        return expected_reward

    def select_guess(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]]) -> str:
        """Select the next guess using VOI strategy."""
        if not candidates:
            return None

        self.current_attempt = len(history) + 1

        if not history:
            return self.select_first_guess(candidates)

        if len(candidates) <= 2:
            return max(candidates, key=lambda c: self.beliefs.get(c, 0))

        best_guess = None
        best_score = -float('inf')

        exploration_factor = max(0.2, 1.0 - (self.current_attempt / 10.0))

        sample_size = min(len(candidates), 200)
        sampled_candidates = random.sample(candidates, sample_size)

        used_guesses = {h[0] for h in history}

        for guess in sampled_candidates:
            if guess in used_guesses:
                continue

            voi = self.calculate_voi(guess, candidates)
            expected_reward = self.calculate_expected_reward(guess, candidates)

            score = (exploration_factor * voi +
                    (1 - exploration_factor) * self.reward_weight * expected_reward)

            if guess in candidates:
                candidate_bonus = 0.5 * (1 - exploration_factor)
                score += candidate_bonus

            if score > best_score:
                best_score = score
                best_guess = guess

        if self.verbose:
            print(f"[Attempt {self.current_attempt}] Selected '{best_guess}' score: {best_score:.4f}")

        return best_guess if best_guess else candidates[0]

    def score_candidates(self, candidates: List[str], history: List[Tuple[str, Tuple[int, int]]], top_k: int = 5) -> List[Tuple[str, float]]:
        """Score and rank candidates, returning top-k (code, score) pairs."""
        if not candidates:
            return []
        if len(candidates) <= top_k:
            return [(c, self.beliefs.get(c, 0)) for c in candidates]

        if not self.beliefs:
            self.initialize_beliefs(candidates)

        self.current_attempt = len(history) + 1
        exploration_factor = max(0.2, 1.0 - (self.current_attempt / 10.0))

        sample_size = min(len(candidates), 200)
        sampled_candidates = random.sample(candidates, sample_size)

        scored = []
        used = {h[0] for h in history}
        for guess in sampled_candidates:
            if guess in used:
                continue
            voi = self.calculate_voi(guess, candidates)
            expected_reward = self.calculate_expected_reward(guess, candidates)
            score = (exploration_factor * voi +
                     (1 - exploration_factor) * self.reward_weight * expected_reward)
            if guess in candidates:
                candidate_bonus = 0.5 * (1 - exploration_factor)
                score += candidate_bonus
            scored.append((guess, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
