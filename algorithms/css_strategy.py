from typing import List, Tuple
import random
import numpy as np

class CSSStrategy:
    def __init__(self):
        self.knowledge_base = {}
        self.attempt_penalty = -1.0  # Default attempt penalty
        self.success_reward = 10.0   # Default success reward
        
    def set_rewards(self, attempt_penalty: float, success_reward: float):
        """Set the reward parameters for the strategy."""
        self.attempt_penalty = attempt_penalty
        self.success_reward = success_reward
        
    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update belief and filter candidates based on feedback."""
        self.knowledge_base[guess] = feedback
        return [word for word in candidates if self._is_consistent(word, guess, feedback)]
    
    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Select the next guess using CSS principles and expected rewards."""
        if not candidates:
            return None

        if len(candidates) == 1:
            return candidates[0]

        # Sample candidates for efficiency
        sample_size = min(len(candidates), 100)
        sample_candidates = random.sample(candidates, sample_size)
        guesses_to_evaluate = sample_candidates

        best_guess = None
        best_score = float('-inf')
            
        for guess in guesses_to_evaluate:
            # Calculate information gain
            info_gain = self._calculate_information_gain(guess, sample_candidates)
            
            # Calculate expected reward
            expected_reward = self._calculate_expected_reward(guess, candidates)
            
            # Combine information gain and expected reward
            score = info_gain + 0.5 * expected_reward  # Weight can be adjusted
            
            if score > best_score:
                best_score = score
                best_guess = guess
                
        return best_guess
    
    def _calculate_expected_reward(self, guess: str, candidates: List[str]) -> float:
        """Calculate the expected reward for a potential guess."""
        if len(candidates) <= 1:
            return self.success_reward + self.attempt_penalty
            
        expected_reward = self.attempt_penalty  # Base penalty for making the attempt
        
        # Calculate probability of success
        if guess in candidates:
            success_prob = 1.0 / len(candidates)
            expected_reward += success_prob * self.success_reward
            
        return expected_reward
    
    def _is_consistent(self, word: str, guess: str, feedback: List[str]) -> bool:
        """
        Check if a word is consistent with the feedback from a guess.
        """
        expected_feedback = self._generate_feedback(word, guess)
        return expected_feedback == feedback
    
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
    
    def _calculate_information_gain(self, guess: str, candidates: List[str]) -> float:
        """Calculate expected information gain using entropy."""
        feedback_counts = {}
        total_candidates = len(candidates)

        for candidate in candidates:
            feedback = tuple(self._generate_feedback(candidate, guess))
            feedback_counts[feedback] = feedback_counts.get(feedback, 0) + 1

        entropy = 0
        for count in feedback_counts.values():
            p = count / total_candidates
            entropy -= p * np.log2(p)

        return entropy
