class GuessingAgent:
    
    def __init__(self, word_list, strategy):
        self.word_list = word_list
        self.strategy = strategy
        self.reset()

    def reset(self):
        self.candidates = self.word_list.copy()
        self.history = []
        self.total_reward = 0

    def update(self, guess, feedback, reward):
        self.candidates = self.strategy.update_belief(self.candidates, guess, feedback)
        self.history.append((guess, feedback))
        self.total_reward += reward

    def select_guess(self):
        guess = self.strategy.select_guess(self.candidates, self.history)
        if guess is None:
            raise RuntimeError("No valid guesses left: candidate list is empty.")
        return guess
        
    def get_total_reward(self):
        return self.total_reward