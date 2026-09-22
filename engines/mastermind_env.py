"""
Mastermind game environment.

Supports multiple variants:
- Classic: 6 colors, 4 pegs (1,296 codes)
- Extended: 8 colors, 4 pegs (4,096 codes)

Feedback is given as:
- Black pegs: correct color in correct position
- White pegs: correct color in wrong position
"""

import random
from itertools import product
from typing import List, Tuple, Optional


# Color sets for different variants
COLORS_CLASSIC = "RGBYOW"  # Red, Green, Blue, Yellow, Orange, White (6 colors)
COLORS_EXTENDED = "RGBYOWPK"  # + Purple, blacK (8 colors)


class MastermindEnv:
    """
    Mastermind game environment.

    Args:
        variant: 'classic' (6 colors) or 'extended' (8 colors)
        num_pegs: Number of positions (default 4)
        max_attempts: Maximum guesses allowed (default 10)
    """

    def __init__(self, variant: str = 'classic', num_pegs: int = 4, max_attempts: int = 10):
        self.variant = variant.lower()
        self.num_pegs = num_pegs
        self.max_attempts = max_attempts

        # Set colors based on variant
        if self.variant == 'classic':
            self.colors = COLORS_CLASSIC
        elif self.variant == 'extended':
            self.colors = COLORS_EXTENDED
        else:
            raise ValueError(f"Unknown variant: {variant}. Use 'classic' or 'extended'.")

        # Generate all possible codes (with repeats allowed)
        self.all_candidates = [''.join(p) for p in product(self.colors, repeat=self.num_pegs)]
        self.candidates = list(self.all_candidates)

        # Reward parameters
        self.base_penalty = -1.0
        self.penalty_increase = 0.5
        self.black_reward = 0.5   # Reward per black peg
        self.white_reward = 0.2   # Reward per white peg
        self.success_reward = 10.0

        self.reset()

    def reset(self, target: Optional[str] = None) -> str:
        """Reset the game with a new target code."""
        if target is not None:
            if not self._is_valid_code(target):
                raise ValueError(f"Invalid code: {target}")
            self.target_code = target
        else:
            self.target_code = random.choice(self.all_candidates)

        self.attempts = 0
        self.history = []
        self.done = False
        self.total_reward = 0
        self.candidates = list(self.all_candidates)
        return self.target_code

    def _is_valid_code(self, code: str) -> bool:
        """Check if a code is valid."""
        if len(code) != self.num_pegs:
            return False
        return all(c in self.colors for c in code)

    def guess(self, code: str) -> Tuple[Tuple[int, int], float]:
        """
        Make a guess and receive feedback.

        Args:
            code: A code string (e.g., "RGBY" for 4 pegs)

        Returns:
            feedback: Tuple (black_pegs, white_pegs)
            reward: Numerical reward for this guess
        """
        if self.done:
            raise Exception("Game over.")

        if not self._is_valid_code(code):
            raise ValueError(f"Invalid code: {code}. Must be {self.num_pegs} characters from {self.colors}")

        self.attempts += 1
        feedback = self._generate_feedback(code)
        self.history.append((code, feedback))

        # Calculate progressive penalty
        current_penalty = self.base_penalty * (1 + self.penalty_increase * (self.attempts - 1))

        # Calculate feedback rewards
        black_pegs, white_pegs = feedback
        feedback_reward = (black_pegs * self.black_reward) + (white_pegs * self.white_reward)

        # Calculate total reward
        reward = current_penalty + feedback_reward

        if code == self.target_code:
            reward += self.success_reward
            self.done = True
        elif self.attempts >= self.max_attempts:
            self.done = True

        self.total_reward += reward
        return feedback, reward

    def _generate_feedback(self, guess: str) -> Tuple[int, int]:
        """
        Generate feedback for a guess.

        Returns:
            Tuple (black_pegs, white_pegs)
        """
        black_pegs = 0
        white_pegs = 0

        target_chars = list(self.target_code)
        guess_chars = list(guess)

        # First pass: count black pegs (correct position)
        for i in range(self.num_pegs):
            if guess_chars[i] == target_chars[i]:
                black_pegs += 1
                target_chars[i] = None
                guess_chars[i] = None

        # Second pass: count white pegs (correct color, wrong position)
        for i in range(self.num_pegs):
            if guess_chars[i] is not None and guess_chars[i] in target_chars:
                white_pegs += 1
                target_chars[target_chars.index(guess_chars[i])] = None

        return (black_pegs, white_pegs)

    def get_total_reward(self) -> float:
        return self.total_reward

    def get_penalty_for_attempt(self, attempt_number: int) -> float:
        """Helper method to get the penalty for a specific attempt number."""
        return self.base_penalty * (1 + self.penalty_increase * (attempt_number - 1))

    @staticmethod
    def feedback_to_string(feedback: Tuple[int, int]) -> str:
        """Convert feedback tuple to human-readable string."""
        black, white = feedback
        return f"{black}B{white}W"

    @staticmethod
    def filter_candidates(candidates: List[str], guess: str, feedback: Tuple[int, int]) -> List[str]:
        """
        Filter candidates based on guess and feedback.
        Returns candidates that would produce the same feedback for the guess.
        """
        return [c for c in candidates if MastermindEnv._compute_feedback(guess, c, len(guess)) == feedback]

    @staticmethod
    def _compute_feedback(guess: str, target: str, num_pegs: int) -> Tuple[int, int]:
        """Compute feedback for a guess against a target."""
        black_pegs = 0
        white_pegs = 0

        target_chars = list(target)
        guess_chars = list(guess)

        for i in range(num_pegs):
            if guess_chars[i] == target_chars[i]:
                black_pegs += 1
                target_chars[i] = None
                guess_chars[i] = None

        for i in range(num_pegs):
            if guess_chars[i] is not None and guess_chars[i] in target_chars:
                white_pegs += 1
                target_chars[target_chars.index(guess_chars[i])] = None

        return (black_pegs, white_pegs)

    def get_all_candidates(self) -> List[str]:
        """Return all valid codes for this variant."""
        return list(self.all_candidates)

    def get_info(self) -> dict:
        """Return information about this game variant."""
        return {
            'variant': self.variant,
            'colors': self.colors,
            'num_colors': len(self.colors),
            'num_pegs': self.num_pegs,
            'search_space': len(self.all_candidates),
            'max_attempts': self.max_attempts,
        }


if __name__ == "__main__":
    # Test both variants
    for variant in ['classic', 'extended']:
        env = MastermindEnv(variant=variant)
        info = env.get_info()
        print(f"\n{variant.upper()} Mastermind:")
        print(f"  Colors: {info['colors']} ({info['num_colors']} colors)")
        print(f"  Pegs: {info['num_pegs']}")
        print(f"  Search space: {info['search_space']} codes")

    # Interactive test
    print("\n" + "="*50)
    env = MastermindEnv(variant='classic')
    target = env.reset()
    print(f"Target code (debug): {target}")
    print(f"Colors available: {env.colors}")

    for i in range(10):
        guess = input(f"Guess {i+1}: ").strip().upper()
        try:
            feedback, reward = env.guess(guess)
            black, white = feedback
            print(f"Feedback: {black} Black, {white} White")
            if guess == target:
                print(f"Correct! Solved in {i+1} attempts.")
                break
        except ValueError as e:
            print(f"Error: {e}")
    else:
        print(f"Out of attempts! The code was: {target}")
