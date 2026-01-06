#!/usr/bin/env python3
"""
Hybrid Strategy: Alternating LLM-CSS
Alternates between LLM and CSS on each turn.
Can start with either LLM or CSS (configurable).

Tests whether alternating between human-like intuition (LLM) and optimal
information theory (CSS) on each guess improves performance.
"""

import os
import csv
import time
import json
import random
import re
import sys
from datetime import datetime
from typing import List, Tuple
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'engines'))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'algorithms'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from wordle_env import WordleEnv
from test_set_loader import get_test_words_only
from css_strategy import CSSStrategy
from voi_strategy import VOIStrategy
from random_strategy import RandomStrategy


# ----------------- Hybrid Strategy -----------------

class AlternatingHybridStrategy:
    """
    Hybrid strategy: Alternates between LLM and an algorithm (CSS/VOI/Random) on each turn.
    """
    def __init__(self, model_name="llama-3.3-70b-instruct", temperature=0.7, start_with="llm", prompt_type="zero-shot", algorithm="css"):
        self.model_name = model_name
        self.temperature = temperature
        self.start_with = start_with.lower()  # "llm" or "algorithm"
        self.prompt_type = prompt_type.lower()  # "zero-shot" or "cot"
        self.algorithm = algorithm.lower()  # "css", "voi", or "random"

        # Initialize the appropriate algorithm strategy
        if self.algorithm == "css":
            self.algo_strategy = CSSStrategy()
        elif self.algorithm == "voi":
            self.algo_strategy = VOIStrategy()
        elif self.algorithm == "random":
            self.algo_strategy = RandomStrategy()
        else:
            raise ValueError(f"Unknown algorithm: {algorithm}. Must be 'css', 'voi', or 'random'")

        self.turn_number = 0
        self.api_base = os.getenv("NAVIGATOR_API_ENDPOINT", "https://api.navigator.uf.edu/v1")

    def update_belief(self, candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
        """Update candidates based on feedback - delegates to algorithm."""
        return self.algo_strategy.update_belief(candidates, guess, feedback)

    def get_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """
        Get next guess: Alternates between LLM and algorithm.
        Turn 1, 3, 5: Use first strategy
        Turn 2, 4, 6: Use second strategy
        """
        self.turn_number = len(history) + 1

        # Determine which strategy to use
        if self.start_with == "llm":
            # LLM on odd turns, algorithm on even turns
            use_llm = (self.turn_number % 2 == 1)
        else:
            # Algorithm on odd turns, LLM on even turns
            use_llm = (self.turn_number % 2 == 0)

        if use_llm:
            return self._get_llm_guess(candidates, history)
        else:
            return self.algo_strategy.select_guess(candidates, history)

    def _get_llm_guess(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Get guess from LLM with retry logic."""
        try:
            import openai
            client = openai.OpenAI(
                api_key=os.getenv("NAVIGATOR_UF_API_KEY"),
                base_url=self.api_base
            )

            prompt = self._build_prompt(candidates, history)

            def api_call():
                return client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=self.temperature,
                    max_tokens=150
                )

            # Retry logic
            for attempt in range(5):
                try:
                    response = api_call()
                    text = response.choices[0].message.content.strip()
                    guess = self._extract_guess(text, history, candidates)
                    if guess:
                        return guess
                    # If no valid guess, fallback to algorithm
                    print(f"LLM failed to provide valid guess, falling back to {self.algorithm.upper()}")
                    return self.algo_strategy.select_guess(candidates, history)
                except Exception as e:
                    print(f"LLM API attempt {attempt+1}/5 failed: {e}")
                    if attempt < 4:
                        time.sleep(2 ** attempt + random.uniform(0, 1))
                    else:
                        # Final fallback to algorithm
                        print(f"LLM failed after all retries, using {self.algorithm.upper()}")
                        return self.algo_strategy.select_guess(candidates, history)

        except Exception as e:
            print(f"LLM initialization failed: {e}, using {self.algorithm.upper()}")
            return self.algo_strategy.select_guess(candidates, history)

    def _build_prompt(self, candidates: List[str], history: List[Tuple[str, List[str]]]) -> str:
        """Build prompt for LLM (supports both zero-shot and CoT)."""
        if self.prompt_type == "cot":
            # Chain-of-thought prompt (structured reasoning)
            prompt = (
                "You are an expert Wordle player. Use brief, structured reasoning.\n"
                "Return output in this exact format:\n"
                "THINKING: <your concise step-by-step reasoning>\n"
                "FINAL: <ONE 5-letter guess only>\n\n"
                "Feedback codes: G=green (correct letter, correct position), "
                "Y=yellow (correct letter, wrong position), -=letter not in word.\n\n"
            )

            if history:
                prompt += "Previous attempts:\n"
                for guess, feedback in history:
                    # Convert feedback to string format
                    fb_str = ''.join(feedback)
                    # Create letter-by-letter breakdown
                    guess_upper = guess.upper()
                    letter_breakdown = "  ".join([f"{guess_upper[i]}:{fb_str[i]}" for i in range(min(len(guess_upper), len(fb_str)))])
                    prompt += f"- Guess: {guess}  Feedback: {fb_str}\n"
                    prompt += f"  Per letter: {letter_breakdown}\n"

            # Show candidates
            if len(candidates) <= 50:
                candidates_str = ", ".join(candidates)
            else:
                sample = candidates[:30] + ["..."] + candidates[-20:]
                candidates_str = ", ".join(sample)

            prompt += (
                f"\nAllowed words remaining: {len(candidates)}\n"
                f"Candidate words: {candidates_str}\n\n"
                "Constraints:\n"
                "• Do NOT repeat previous guesses.\n"
                "• The FINAL line must be exactly ONE valid 5-letter word from the allowed list.\n"
                "• Keep THINKING concise (1-5 short lines)."
            )
        else:
            # Zero-shot prompt (original format)
            prompt = "You are playing Wordle. Your goal is to guess a 5-letter word.\n\n"

            if history:
                prompt += "Previous guesses:\n"
                for guess, feedback in history:
                    feedback_str = ''.join(['🟩' if f == 'G' else '🟨' if f == 'Y' else '⬜' for f in feedback])
                    prompt += f"{guess}: {feedback_str}\n"
                prompt += "\n"

            # Show candidates if pool is reasonably small
            if len(candidates) <= 30:
                prompt += f"Remaining possible words ({len(candidates)}): {', '.join(candidates)}\n\n"
            elif len(candidates) <= 100:
                sample = random.sample(candidates, 20)
                prompt += f"Remaining possible words ({len(candidates)}, showing sample): {', '.join(sample)}\n\n"
            else:
                prompt += f"Number of remaining possible words: {len(candidates)}\n\n"

            prompt += "Based on the feedback, what should the next guess be?\n"
            prompt += "Return ONLY a single 5-letter word in uppercase, nothing else.\n"
            prompt += "Your guess: "

        return prompt

    def _extract_guess(self, text: str, history: List[Tuple[str, List[str]]], candidates: List[str]) -> str:
        """Extract valid 5-letter word from LLM response (supports CoT format)."""
        if not text:
            return None

        # Get already used words
        used = {g for g, _ in history}

        # For CoT format, try to extract from FINAL: line first
        if self.prompt_type == "cot":
            final_match = re.search(r'FINAL\s*:\s*([A-Za-z]{5})\b', text, re.IGNORECASE)
            if final_match:
                word = final_match.group(1).upper()
                if word not in used:
                    return word

        # Find all 5-letter words in response
        words = re.findall(r'\b[A-Za-z]{5}\b', text.upper())

        # Prefer words from candidate list
        for word in words:
            if word not in used and word in candidates:
                return word

        # If no candidate found, try any valid unused word
        for word in words:
            if word not in used:
                return word

        return None


# ----------------- Guessing Agent -----------------

class GuessingAgent:
    """Agent that uses the hybrid strategy to play Wordle."""
    def __init__(self, word_list, strategy):
        self.word_list = word_list
        self.strategy = strategy
        self.candidates = list(word_list)
        self.history = []

    def reset(self):
        """Reset agent for new game."""
        self.candidates = list(self.word_list)
        self.history = []
        self.strategy.turn_number = 0

    def select_guess(self):
        """Select next guess using strategy."""
        return self.strategy.get_guess(self.candidates, self.history)

    def update(self, guess, feedback, reward):
        """Update agent state after guess."""
        # Convert feedback to string format if needed
        if feedback and isinstance(feedback[0], int):
            str_feedback = ['G' if f == 2 else 'Y' if f == 1 else '-' for f in feedback]
        else:
            str_feedback = feedback

        self.history.append((guess, str_feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, str_feedback)


# ----------------- Distance Metrics -----------------

def hamming_distance(word1: str, word2: str) -> int:
    """Calculate Hamming distance between two words."""
    return sum(c1 != c2 for c1, c2 in zip(word1.upper(), word2.upper()))

def levenshtein_distance(word1: str, word2: str) -> int:
    """Calculate Levenshtein distance between two words."""
    if len(word1) < len(word2):
        return levenshtein_distance(word2, word1)
    if len(word2) == 0:
        return len(word1)

    previous_row = range(len(word2) + 1)
    for i, c1 in enumerate(word1):
        current_row = [i + 1]
        for j, c2 in enumerate(word2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


# ----------------- Main Evaluation -----------------

def run_evaluation(num_games=100, model_name="llama-3.3-70b-instruct", start_with="llm", prompt_type="zero-shot", algorithm="css"):
    """Run evaluation on canonical test set."""

    print("="*80)
    print(f"HYBRID STRATEGY EVALUATION: Alternating LLM-{algorithm.upper()}")
    print("="*80)
    print(f"Model: {model_name}")
    print(f"Prompt Type: {prompt_type}")
    print(f"Algorithm: {algorithm.upper()}")

    if start_with.lower() == "llm":
        print(f"Strategy: LLM on odd turns (1,3,5), {algorithm.upper()} on even turns (2,4,6)")
    else:
        print(f"Strategy: {algorithm.upper()} on odd turns (1,3,5), LLM on even turns (2,4,6)")

    print(f"Games: {num_games}")
    print("="*80)

    # Load word list and test set
    script_dir = Path(__file__).parent.parent.parent
    with open(script_dir / 'wordlist' / 'wordlist.txt', 'r') as f:
        word_list = [line.strip().upper() for line in f if line.strip()]

    test_words = get_test_words_only()[:num_games]

    # Initialize strategy and agent
    strategy = AlternatingHybridStrategy(model_name=model_name, start_with=start_with, prompt_type=prompt_type, algorithm=algorithm)
    agent = GuessingAgent(word_list, strategy)

    # Results storage
    results = []
    wins = 0
    total_attempts = 0

    # Run games
    for game_num, target_word in enumerate(test_words, 1):
        print(f"\nGame {game_num}/{num_games}: Target = {target_word}")

        env = WordleEnv([target_word])
        env.reset()
        agent.reset()

        game_result = {
            'game_number': game_num,
            'target_word': target_word,
            'won': False,
            'attempts': 0,
            'guesses': [],
            'feedbacks': [],
            'hamming_distances': [],
            'levenshtein_distances': [],
            'strategy_used': []  # Track which strategy was used for each guess
        }

        # Play game (max 6 attempts)
        for attempt in range(1, 7):
            guess = agent.select_guess()
            if not guess:
                print(f"  Attempt {attempt}: No valid guess available")
                break

            feedback, reward = env.guess(guess)
            agent.update(guess, feedback, reward)

            # Calculate distances
            ham_dist = hamming_distance(guess, target_word)
            lev_dist = levenshtein_distance(guess, target_word)

            # Convert feedback to string (feedback is already strings from WordleEnv)
            feedback_str = ''.join(feedback)

            # Determine which strategy was used
            if start_with.lower() == "llm":
                strategy_used = "LLM" if attempt % 2 == 1 else "CSS"
            else:
                strategy_used = "CSS" if attempt % 2 == 1 else "LLM"

            game_result['strategy_used'].append(strategy_used)

            print(f"  Attempt {attempt} [{strategy_used}]: {guess} -> {feedback_str} (H:{ham_dist}, L:{lev_dist})")

            game_result['guesses'].append(guess)
            game_result['feedbacks'].append(feedback_str)
            game_result['hamming_distances'].append(ham_dist)
            game_result['levenshtein_distances'].append(lev_dist)
            game_result['attempts'] = attempt

            # Check if won (feedback is strings: "G", "Y", "-")
            if all(f == "G" for f in feedback):
                game_result['won'] = True
                wins += 1
                total_attempts += attempt
                print(f"  ✓ Won in {attempt} attempts!")
                break

        if not game_result['won']:
            print(f"  ✗ Failed to find word")

        results.append(game_result)

    # Calculate statistics
    win_rate = wins / num_games
    avg_attempts = total_attempts / wins if wins > 0 else 0

    print("\n" + "="*80)
    print("RESULTS SUMMARY")
    print("="*80)
    print(f"Games played: {num_games}")
    print(f"Wins: {wins}")
    print(f"Win rate: {win_rate*100:.1f}%")
    print(f"Average attempts (when won): {avg_attempts:.2f}")
    print("="*80)

    # Save results
    output_dir = script_dir / 'results' / 'hybrids'
    output_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prompt_suffix = "_cot" if prompt_type == "cot" else ""
    algo_suffix = f"_{algorithm}" if algorithm != "css" else ""
    csv_file = output_dir / f"alternating_{start_with}_first_{model_name}{algo_suffix}{prompt_suffix}_{timestamp}.csv"

    with open(csv_file, 'w', newline='') as f:
        writer = csv.writer(f)

        # Header
        header = ['game_number', 'target_word', 'won', 'attempts']
        for i in range(1, 7):
            header.extend([f'guess_{i}', f'feedback_{i}', f'hamming_{i}', f'levenshtein_{i}', f'strategy_{i}'])
        writer.writerow(header)

        # Data rows
        for result in results:
            row = [result['game_number'], result['target_word'], result['won'], result['attempts']]
            for i in range(6):
                if i < len(result['guesses']):
                    row.extend([
                        result['guesses'][i],
                        result['feedbacks'][i],
                        result['hamming_distances'][i],
                        result['levenshtein_distances'][i],
                        result['strategy_used'][i] if i < len(result['strategy_used']) else ''
                    ])
                else:
                    row.extend(['', '', '', '', ''])
            writer.writerow(row)

    # Save summary JSON
    summary = {
        'strategy': f'alternating_{start_with}_first',
        'model_name': model_name,
        'start_with': start_with,
        'prompt_type': prompt_type,
        'algorithm': algorithm,
        'total_games': num_games,
        'wins': wins,
        'win_rate': win_rate,
        'avg_attempts_when_won': avg_attempts,
        'timestamp': timestamp
    }

    json_file = output_dir / f"summary_alternating_{start_with}_first_{model_name}{algo_suffix}{prompt_suffix}_{timestamp}.json"
    with open(json_file, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\nResults saved to:")
    print(f"  {csv_file}")
    print(f"  {json_file}")

    return results, summary


if __name__ == "__main__":
    # Get configuration from environment
    model_name = os.getenv("MODEL", "llama-3.3-70b-instruct")
    num_games = int(os.getenv("NUM_GAMES", "100"))
    start_with = os.getenv("START_WITH", "llm")  # "llm" or "algorithm"
    prompt_type = os.getenv("PROMPT_TYPE", "zero-shot")  # "zero-shot" or "cot"
    algorithm = os.getenv("ALGORITHM", "css")  # "css", "voi", or "random"

    # Check API key
    if not os.getenv("NAVIGATOR_UF_API_KEY"):
        print("ERROR: NAVIGATOR_UF_API_KEY environment variable not set")
        sys.exit(1)

    run_evaluation(num_games=num_games, model_name=model_name, start_with=start_with, prompt_type=prompt_type, algorithm=algorithm)
