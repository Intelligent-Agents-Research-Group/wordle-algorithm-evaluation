import random

class WordleEnv:
    
    def __init__(self, word_list, max_attempts=6):
        self.word_list = word_list
        self.max_attempts = max_attempts
        # Base penalty parameters
        self.base_penalty = -1.0
        self.penalty_increase = 0.5  # 50% increase per attempt
        # Feedback reward parameters
        self.green_reward = 0.5  # Reward for correct letter in correct position
        self.yellow_reward = 0.2  # Reward for correct letter in wrong position
        self.success_reward = 10.0  # Reward for finding the word
        self.reset()

    def reset(self):
        self.target_word = random.choice(self.word_list)
        self.attempts = 0
        self.history = []
        self.done = False
        self.total_reward = 0
        return self.target_word

    def guess(self, word):
        if self.done:
            raise Exception("Game over.")
        
        self.attempts += 1
        feedback = self._generate_feedback(word)
        self.history.append((word, feedback))
        
        # Calculate progressive penalty
        current_penalty = self.base_penalty * (1 + self.penalty_increase * (self.attempts - 1))
        
        # Calculate feedback rewards
        feedback_reward = 0
        for f in feedback:
            if f == "G":
                feedback_reward += self.green_reward
            elif f == "Y":
                feedback_reward += self.yellow_reward
        
        # Calculate total reward
        reward = current_penalty + feedback_reward
        
        if word == self.target_word:
            reward += self.success_reward  # Add success reward if word is found
            self.done = True
        elif self.attempts >= self.max_attempts:
            self.done = True
            
        self.total_reward += reward
        return feedback, reward

    def _generate_feedback(self, guess):
        feedback = ["-"] * 5
        target_chars = list(self.target_word)
        guess_chars = list(guess)

        for i in range(5):
            if guess_chars[i] == target_chars[i]:
                feedback[i] = "G"
                target_chars[i] = None  # used
                guess_chars[i] = None

        for i in range(5):
            if guess_chars[i] and guess_chars[i] in target_chars:
                feedback[i] = "Y"
                target_chars[target_chars.index(guess_chars[i])] = None

        return feedback

    def get_total_reward(self):
        return self.total_reward

    def get_penalty_for_attempt(self, attempt_number):
        """Helper method to get the penalty for a specific attempt number."""
        return self.base_penalty * (1 + self.penalty_increase * (attempt_number - 1))

if __name__ == "__main__":
    word_list = ["CRANE", "CLEAN", "PLANE", "TRAIL", "FLAIR"]
    env = WordleEnv(word_list)
    target = env.reset()
    print("Target word (debug):", target)

    for i in range(6):
        guess = input(f"Guess {i+1}: ").strip().upper()
        feedback, reward = env.guess(guess)
        print("Feedback:", feedback)
        if guess == target:
            print("Correct!")
            break
    else:
        print("Out of attempts! The word was:", target)