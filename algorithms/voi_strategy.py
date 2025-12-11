import numpy as np
from typing import List, Tuple
import random
from collections import defaultdict, Counter

class VOIStrategy:
    def __init__(self, verbose: bool = False, green_match_weight: float = 0.3, 
                 green_voi_weight: float = 0.5, letter_freq_multiplier: float = 1.0):
        self.verbose = verbose
        self.beliefs = {}  
        self.feedback_cache = {} 
        self.letter_frequencies = {}  
        self.position_frequencies = [defaultdict(int) for _ in range(5)] 
        self.common_words = set()  
        self.attempt_penalty = -1.0  # Default attempt penalty
        self.success_reward = 10.0   # Default success reward
        
        # Only 3 configurable parameters - the most impactful ones
        self.green_match_weight = green_match_weight
        self.green_voi_weight = green_voi_weight
        self.letter_freq_multiplier = letter_freq_multiplier
        
        # Fixed reasonable defaults for other parameters
        self.yellow_match_weight = 0.05  # Fixed based on optimization results
        self.gray_match_weight = 0.0     # Fixed - gray matches not useful
        self.yellow_voi_weight = 0.1     # Fixed - much less important than green
        self.reward_weight = 0.5         # Fixed - balanced approach
        self.shared_letters_weight = 0.0 # Fixed - not very impactful
        
        # NEW: Track attempt number to adjust exploration vs exploitation
        self.current_attempt = 0
        
    def initialize_beliefs(self, word_list: List[str]):
        """Initialize beliefs to a uniform distribution, but still calculate letter/position frequencies for other uses."""
        self.beliefs = {}
        self.letter_frequencies = Counter()
        self.position_frequencies = [defaultdict(int) for _ in range(5)]

        # Calculate letter frequencies (for other uses, not for beliefs)
        for word in word_list:
            for i, letter in enumerate(word):
                self.letter_frequencies[letter] += 1
                self.position_frequencies[i][letter] += 1

        total_words = len(word_list)
        for letter in self.letter_frequencies:
            self.letter_frequencies[letter] /= total_words
        for pos_freq in self.position_frequencies:
            for letter in pos_freq:
                pos_freq[letter] /= total_words

        # Uniform initial beliefs
        for word in word_list:
            self.beliefs[word] = 1.0 / total_words
    
    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update beliefs based on the feedback from a guess and return filtered candidates."""
        if not self.beliefs:  
            self.initialize_beliefs(candidates)
        
        feedback_int = [2 if f == "G" else 1 if f == "Y" else 0 for f in feedback]
        
        total_prob = 0
        new_beliefs = {}
        
        # FIXED: Properly filter candidates based on feedback constraints
        filtered_candidates = []
        for word in candidates:
            expected_feedback = self.get_feedback(guess, word)
            
            # Only keep candidates that match the feedback exactly
            if expected_feedback == feedback_int:
                filtered_candidates.append(word)
                
                match_score = self.calculate_match_score(expected_feedback, feedback_int)
                word_score = self.beliefs[word] * match_score
                
                for i, (exp, act) in enumerate(zip(expected_feedback, feedback_int)):
                    if exp == act and exp > 0:  
                        letter = guess[i]
                        word_score *= (1 + self.letter_freq_multiplier * self.letter_frequencies.get(letter, 0))
                
                new_beliefs[word] = word_score
                total_prob += word_score
            
        # Normalize beliefs only for filtered candidates
        if total_prob > 0:
            for word in filtered_candidates:
                self.beliefs[word] = new_beliefs[word] / total_prob
        else:
            # Fallback: uniform distribution over filtered candidates
            for word in filtered_candidates:
                self.beliefs[word] = 1.0 / len(filtered_candidates) if filtered_candidates else 0
                
        return filtered_candidates
    

    def calculate_match_score(self, expected: List[int], actual: List[int]) -> float:
        """Calculate a similarity score between feedback patterns based on total counts."""
        if expected == actual:
            return 1.0

        expected_counter = Counter(expected)
        actual_counter = Counter(actual)

        # Match feedback type counts (2 = green, 1 = yellow, 0 = gray)
        green_matches = min(expected_counter[2], actual_counter[2])
        yellow_matches = min(expected_counter[1], actual_counter[1])
        gray_matches = min(expected_counter[0], actual_counter[0])

        base_score = 0.1
        base_score += self.green_match_weight * green_matches
        base_score += self.yellow_match_weight * yellow_matches
        base_score += self.gray_match_weight * gray_matches

        return min(base_score, 1.0)
    
    def get_feedback(self, guess: str, target: str) -> List[int]:
        """Get feedback from cache or calculate it."""
        key = (guess, target)
        if key not in self.feedback_cache:
            self.feedback_cache[key] = self.calculate_feedback(guess, target)
        return self.feedback_cache[key]
    
    def calculate_feedback(self, guess: str, target: str) -> List[int]:
        """Calculate what feedback a guess would get against a target word."""
        feedback = [0] * len(guess)
        used = [False] * len(target)
        
        for i in range(len(guess)):
            if guess[i] == target[i]:
                feedback[i] = 2
                used[i] = True
        
        for i in range(len(guess)):
            if feedback[i] == 0:  
                for j in range(len(target)):
                    if not used[j] and guess[i] == target[j]:
                        feedback[i] = 1
                        used[j] = True
                        break
        
        return feedback
    
    def calculate_voi(self, guess: str, candidates: List[str]) -> float:
        """Calculate the Value of Information for a potential guess."""
        if len(candidates) <= 1:
            return 0.0
            
        feedback_groups = defaultdict(list)
        for target in candidates:
            feedback = self.get_feedback(guess, target)
            feedback_groups[tuple(feedback)].append(target)
        
        # IMPROVED: Calculate expected entropy reduction (information gain)
        entropy_before = self.calculate_entropy(candidates)
        expected_entropy_after = 0
        
        for feedback, group in feedback_groups.items():
            group_prob = sum(self.beliefs.get(word, 0) for word in group)
            if group_prob > 0:
                # Calculate entropy within this group
                group_entropy = 0
                for word in group:
                    p = self.beliefs.get(word, 0) / group_prob
                    if p > 0:
                        group_entropy -= p * np.log2(p)
                
                # Weight by probability of this feedback occurring
                expected_entropy_after += group_prob * group_entropy
        
        # Information gain is the reduction in entropy
        info_gain = entropy_before - expected_entropy_after
        
        # IMPROVED: Add diversity bonus - penalize guesses that create large groups
        max_group_size = max(len(group) for group in feedback_groups.values())
        diversity_bonus = -0.1 * (max_group_size / len(candidates))  # Penalty for large groups
        
        return info_gain + diversity_bonus
    
    def calculate_entropy(self, candidates: List[str]) -> float:
        """Calculate the current entropy of the belief distribution."""
        entropy = 0
        for word in candidates:
            p = self.beliefs.get(word, 0)
            if p > 0:
                entropy -= p * np.log2(p)
        return entropy
    
    def select_first_guess(self, candidates: List[str]) -> str:
        """Select an optimal first guess based on letter frequencies and patterns."""
        # IMPROVED: Add some randomization and better scoring
        best_guesses = []
        best_score = -float('inf')
        
        # Sample candidates if list is too large
        sample_size = min(len(candidates), 500)
        sampled_candidates = random.sample(candidates, sample_size)
        
        for word in sampled_candidates:
            score = 0
            used_letters = set()
            
            # Score based on unique letters (diversity)
            for i, letter in enumerate(word):
                if letter not in used_letters:
                    # Prioritize common letters
                    score += self.letter_frequencies.get(letter, 0) * 3
                    used_letters.add(letter)
                # Position-specific frequency
                score += self.position_frequencies[i].get(letter, 0) * 0.5
            
            # Bonus for 5 unique letters (maximum information)
            if len(used_letters) == 5:
                score += 0.5
            
            if score > best_score:
                best_score = score
                best_guesses = [word]
            elif score == best_score:
                best_guesses.append(word)
        
        # FIXED: Return a random choice from top guesses to avoid always picking AEROS
        return random.choice(best_guesses) if best_guesses else candidates[0]
    
    def set_rewards(self, attempt_penalty: float, success_reward: float):
        """Set the reward parameters for the strategy."""
        self.attempt_penalty = attempt_penalty
        self.success_reward = success_reward
        
    def calculate_expected_reward(self, guess: str, candidates: List[str]) -> float:
        """Calculate the expected reward for a potential guess."""
        if len(candidates) <= 1:
            return self.success_reward + self.attempt_penalty  # If only one candidate, we'll get it right
            
        feedback_groups = defaultdict(list)
        for target in candidates:
            feedback = self.get_feedback(guess, target)
            feedback_groups[tuple(feedback)].append(target)
            
        expected_reward = self.attempt_penalty  # Base penalty for making the attempt
        
        # Calculate probability of success and expected reward
        for feedback, group in feedback_groups.items():
            group_prob = sum(self.beliefs.get(word, 0) for word in group)
            if guess in group:  # If the guess is in the group, we might win
                expected_reward += group_prob * self.success_reward
                
        return expected_reward
    
    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[int]]]) -> str:
        """Select the next guess using VOI strategy and expected rewards."""
        if not candidates:
            print("[VOIStrategy] Warning: No candidates left to guess from.")
            return None
        
        # Track attempt number
        self.current_attempt = len(history) + 1
            
        if not history: 
            return self.select_first_guess(candidates)
        
        # IMPROVED: If only a few candidates left, just pick the most likely one
        if len(candidates) <= 2:
            # Pick the candidate with highest belief
            return max(candidates, key=lambda w: self.beliefs.get(w, 0))
        
        best_guess = None
        best_score = -float('inf')
        
        # IMPROVED: Adaptive exploration based on attempt number
        # Later attempts should be more exploitative (pick from remaining candidates)
        exploration_factor = max(0.2, 1.0 - (self.current_attempt / 6.0))
        
        # Sample candidates for efficiency
        sample_size = min(len(candidates), 200)
        sampled_candidates = random.sample(candidates, sample_size)
        
        for guess in sampled_candidates:
            if guess not in [h[0] for h in history]:
                # Calculate both VOI and expected reward
                voi = self.calculate_voi(guess, candidates)
                expected_reward = self.calculate_expected_reward(guess, candidates)
                
                # IMPROVED: Adaptive weighting based on attempt number
                # Early attempts: prioritize VOI (exploration)
                # Late attempts: prioritize expected reward (exploitation)
                score = (exploration_factor * voi + 
                        (1 - exploration_factor) * self.reward_weight * expected_reward)
                
                # IMPROVED: Bonus for guessing from remaining candidates
                if guess in candidates:
                    candidate_bonus = 0.5 * (1 - exploration_factor)  # Increases as attempts increase
                    score += candidate_bonus
                
                if score > best_score:
                    best_score = score
                    best_guess = guess
        
        if self.verbose:
            print(f"[Attempt {self.current_attempt}] Selected guess '{best_guess}' with score: {best_score:.4f} (candidates: {len(candidates)})")
        
        return best_guess if best_guess else candidates[0]

