import random
from typing import List, Tuple

class PureRandomStrategy:
    def __init__(self):
        self.word_list = None
        
    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        return candidates
    
    def select_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
    
        if self.word_list is None:
            self.word_list = candidates
            
        return random.choice(self.word_list) 