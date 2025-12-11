import random
from typing import List, Tuple

class RandomStrategy:
    def __init__(self):
        pass 
        
    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Filter candidates based on feedback consistency."""
        return [word for word in candidates if self._is_consistent(word, guess, feedback)]
    
    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Select a random guess from remaining candidates."""
        return random.choice(candidates) if candidates else None
    
    def _is_consistent(self, word: str, guess: str, feedback: List[str]) -> bool:
        """Check if a word is consistent with the feedback from a guess."""
        return self._generate_feedback(word, guess) == feedback

    def _generate_feedback(self, target: str, guess: str) -> List[str]:
        """Generate feedback for a guess against a target word."""
        feedback = ["-"] * 5
        target_chars = list(target)
        guess_chars = list(guess)

        # Mark greens
        for i in range(5):
            if guess_chars[i] == target_chars[i]:
                feedback[i] = "G"
                target_chars[i] = None
                guess_chars[i] = None

        # Mark yellows
        for i in range(5):
            if guess_chars[i] and guess_chars[i] in target_chars:
                feedback[i] = "Y"
                target_chars[target_chars.index(guess_chars[i])] = None

        return feedback
