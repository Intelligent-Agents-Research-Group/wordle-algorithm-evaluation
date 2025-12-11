#!/usr/bin/env python3
"""
Comprehensive evaluation of all algorithms (basic and hybrid strategies).

Tests 8 strategies on 100 games using the canonical test set:
- 34 words from Tier 1 (most common words)
- 33 words from Tier 2
- 33 words from Tier 3

Uses canonical_test_set.csv to ensure all evaluations (algorithms and LLMs)
test on identical words in identical order for fair comparison.

Calculates both Hamming and Levenshtein distances for each guess.
Outputs detailed CSV with all metrics for analysis.
"""

import random
import csv
from datetime import datetime
from typing import List, Tuple

from wordle_env import WordleEnv
from css_strategy import CSSStrategy
from voi_strategy import VOIStrategy
from random_strategy import RandomStrategy
from pure_random_strategy import PureRandomStrategy
from test_set_loader import get_test_words_only


def load_word_list(filename='words'):
    """Load word list from file."""
    with open(filename, 'r') as f:
        return [word.strip().upper() for word in f.readlines() if len(word.strip()) == 5]


def create_test_set(word_list, num_words=100, seed=42):
    """Create a standardized test set."""
    random.seed(seed)
    return random.sample(word_list, num_words)


def hamming_distance(word1: str, word2: str) -> int:
    """Calculate Hamming distance between two words."""
    return sum(c1 != c2 for c1, c2 in zip(word1, word2))


def levenshtein_distance(word1: str, word2: str) -> int:
    """
    Calculate Levenshtein distance between two words.
    Implementation using dynamic programming.
    """
    if len(word1) < len(word2):
        return levenshtein_distance(word2, word1)

    if len(word2) == 0:
        return len(word1)

    previous_row = range(len(word2) + 1)
    for i, c1 in enumerate(word1):
        current_row = [i + 1]
        for j, c2 in enumerate(word2):
            # Cost of insertions, deletions, or substitutions
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def filter_candidates_by_feedback(candidates: List[str], guess: str, feedback: List[str]) -> List[str]:
    """Filter candidates based on feedback."""
    filtered = []
    for word in candidates:
        if is_consistent(word, guess, feedback):
            filtered.append(word)
    return filtered


def is_consistent(word: str, guess: str, feedback: List[str]) -> bool:
    """Check if a word is consistent with the feedback."""
    expected_feedback = generate_feedback(word, guess)
    return expected_feedback == feedback


def generate_feedback(target: str, guess: str) -> List[str]:
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


class HybridAgent:
    """Agent that can switch or alternate between strategies."""

    def __init__(self, word_list: List[str], strategy_a, strategy_b,
                 mode: str = "switch_after_1", switch_point: int = 1):
        """
        mode options:
        - "switch_after_1": Use strategy_a for first guess, then strategy_b
        - "alternating_a_first": Alternate starting with strategy_a (A-B-A-B-A-B)
        - "alternating_b_first": Alternate starting with strategy_b (B-A-B-A-B-A)
        """
        self.word_list = word_list
        self.strategy_a = strategy_a
        self.strategy_b = strategy_b
        self.mode = mode
        self.switch_point = switch_point
        self.reset()

    def reset(self):
        self.candidates = self.word_list.copy()
        self.history = []
        self.attempt_count = 0

    def select_guess(self) -> str:
        """Select guess based on mode."""
        if self.mode == "switch_after_1":
            if self.attempt_count < self.switch_point:
                return self.strategy_a.select_guess(self.candidates, self.history)
            else:
                return self.strategy_b.select_guess(self.candidates, self.history)

        elif self.mode == "alternating_a_first":
            if self.attempt_count % 2 == 0:
                return self.strategy_a.select_guess(self.candidates, self.history)
            else:
                return self.strategy_b.select_guess(self.candidates, self.history)

        elif self.mode == "alternating_b_first":
            if self.attempt_count % 2 == 0:
                return self.strategy_b.select_guess(self.candidates, self.history)
            else:
                return self.strategy_a.select_guess(self.candidates, self.history)

    def update(self, guess: str, feedback: List[str]):
        """Update both strategies."""
        self.attempt_count += 1
        self.history.append((guess, feedback))
        self.candidates = filter_candidates_by_feedback(self.candidates, guess, feedback)
        self.strategy_a.update_belief(self.candidates, guess, feedback)
        self.strategy_b.update_belief(self.candidates, guess, feedback)


class SimpleAgent:
    """Agent for single-strategy testing."""

    def __init__(self, word_list: List[str], strategy):
        self.word_list = word_list
        self.strategy = strategy
        self.reset()

    def reset(self):
        self.candidates = self.word_list.copy()
        self.history = []

    def select_guess(self) -> str:
        return self.strategy.select_guess(self.candidates, self.history)

    def update(self, guess: str, feedback: List[str]):
        self.history.append((guess, feedback))
        self.candidates = self.strategy.update_belief(self.candidates, guess, feedback)


def run_strategy_test(word_list: List[str], test_words: List[str],
                     strategy_name: str, agent_factory) -> List[dict]:
    """Run test for a single strategy and return detailed results."""
    print(f"\nTesting {strategy_name}...")

    results = []

    for game_id, target_word in enumerate(test_words):
        env = WordleEnv(word_list)
        env.target_word = target_word
        env.attempts = 0
        env.done = False

        agent = agent_factory()

        guesses = []
        feedbacks = []
        hamming_distances = []
        levenshtein_distances = []
        win = False
        attempts_to_win = 0

        for attempt in range(6):
            try:
                guess = agent.select_guess()
                if not guess:
                    break

                feedback, reward = env.guess(guess)
                agent.update(guess, feedback)

                guesses.append(guess)
                feedbacks.append(''.join(feedback))
                hamming_distances.append(hamming_distance(guess, target_word))
                levenshtein_distances.append(levenshtein_distance(guess, target_word))

                if guess == target_word:
                    win = True
                    attempts_to_win = attempt + 1
                    break

            except Exception as e:
                print(f"  Error in game {game_id + 1} ({target_word}), attempt {attempt + 1}: {e}")
                break

        if not win:
            attempts_to_win = 7

        # Pad to 6 attempts
        while len(guesses) < 6:
            guesses.append('')
            feedbacks.append('')
            hamming_distances.append('')
            levenshtein_distances.append('')

        results.append({
            'strategy': strategy_name,
            'game_number': game_id + 1,
            'target_word': target_word,
            'won': win,
            'attempts': attempts_to_win,
            'total_reward': env.get_total_reward() if win else -10,
            'guess_1': guesses[0], 'feedback_1': feedbacks[0],
            'hamming_1': hamming_distances[0], 'levenshtein_1': levenshtein_distances[0],
            'guess_2': guesses[1], 'feedback_2': feedbacks[1],
            'hamming_2': hamming_distances[1], 'levenshtein_2': levenshtein_distances[1],
            'guess_3': guesses[2], 'feedback_3': feedbacks[2],
            'hamming_3': hamming_distances[2], 'levenshtein_3': levenshtein_distances[2],
            'guess_4': guesses[3], 'feedback_4': feedbacks[3],
            'hamming_4': hamming_distances[3], 'levenshtein_4': levenshtein_distances[3],
            'guess_5': guesses[4], 'feedback_5': feedbacks[4],
            'hamming_5': hamming_distances[4], 'levenshtein_5': levenshtein_distances[4],
            'guess_6': guesses[5], 'feedback_6': feedbacks[5],
            'hamming_6': hamming_distances[5], 'levenshtein_6': levenshtein_distances[5],
        })

    # Calculate summary statistics
    wins = sum(1 for r in results if r['won'])
    total_attempts = sum(r['attempts'] for r in results if r['won'])
    win_rate = wins / len(test_words) if test_words else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0

    print(f"  {strategy_name}: {win_rate:.1%} win rate ({wins}/{len(test_words)}), "
          f"avg {avg_attempts:.2f} attempts")

    return results


def main():
    print("=" * 80)
    print("Comprehensive Strategy Comparison")
    print("=" * 80)
    print("\nTesting all strategies on same 100 words with distance metrics")

    # Load word list
    word_list = load_word_list()
    print(f"\nLoaded {len(word_list)} words")

    # Load canonical test set (ensures algorithms and LLMs use same words)
    test_words = get_test_words_only()
    print(f"Testing on {len(test_words)} words from canonical test set")

    all_results = []

    # Define all strategies to test
    strategies = [
        # Pure strategies
        ("pure_random", lambda: SimpleAgent(word_list, PureRandomStrategy())),
        ("random", lambda: SimpleAgent(word_list, RandomStrategy())),
        ("css", lambda: SimpleAgent(word_list, CSSStrategy())),
        ("voi", lambda: SimpleAgent(word_list, VOIStrategy())),

        # Hybrid strategies - one-time switch
        ("css_then_voi", lambda: HybridAgent(
            word_list, CSSStrategy(), VOIStrategy(), mode="switch_after_1", switch_point=1
        )),
        ("voi_then_css", lambda: HybridAgent(
            word_list, VOIStrategy(), CSSStrategy(), mode="switch_after_1", switch_point=1
        )),

        # Alternating strategies
        ("css_voi_alternating", lambda: HybridAgent(
            word_list, CSSStrategy(), VOIStrategy(), mode="alternating_a_first"
        )),
        ("voi_css_alternating", lambda: HybridAgent(
            word_list, VOIStrategy(), CSSStrategy(), mode="alternating_b_first"
        )),
    ]

    print("\n" + "=" * 80)
    print("Running Tests")
    print("=" * 80)

    for strategy_name, agent_factory in strategies:
        results = run_strategy_test(word_list, test_words, strategy_name, agent_factory)
        all_results.extend(results)

    # Write results to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = f"all_strategies_comprehensive_{timestamp}.csv"

    headers = [
        'strategy', 'game_number', 'target_word', 'won', 'attempts', 'total_reward',
        'guess_1', 'feedback_1', 'hamming_1', 'levenshtein_1',
        'guess_2', 'feedback_2', 'hamming_2', 'levenshtein_2',
        'guess_3', 'feedback_3', 'hamming_3', 'levenshtein_3',
        'guess_4', 'feedback_4', 'hamming_4', 'levenshtein_4',
        'guess_5', 'feedback_5', 'hamming_5', 'levenshtein_5',
        'guess_6', 'feedback_6', 'hamming_6', 'levenshtein_6',
    ]

    with open(csv_filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(all_results)

    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)

    # Calculate summary statistics by strategy
    from collections import defaultdict
    strategy_stats = defaultdict(lambda: {'wins': 0, 'total_games': 0, 'total_attempts': 0})

    for result in all_results:
        strategy = result['strategy']
        strategy_stats[strategy]['total_games'] += 1
        if result['won']:
            strategy_stats[strategy]['wins'] += 1
            strategy_stats[strategy]['total_attempts'] += result['attempts']

    print("\n{:<25} {:>10} {:>12} {:>15}".format(
        "Strategy", "Win Rate", "Wins/Games", "Avg Attempts"))
    print("-" * 80)

    for strategy in ['pure_random', 'random', 'css', 'voi',
                     'css_then_voi', 'voi_then_css',
                     'css_voi_alternating', 'voi_css_alternating']:
        stats = strategy_stats[strategy]
        win_rate = stats['wins'] / stats['total_games'] if stats['total_games'] > 0 else 0
        avg_attempts = stats['total_attempts'] / stats['wins'] if stats['wins'] > 0 else 0
        print("{:<25} {:>9.1%} {:>6}/{:<5} {:>15.2f}".format(
            strategy, win_rate, stats['wins'], stats['total_games'], avg_attempts))

    print("\n" + "=" * 80)
    print(f"✓ Results saved to: {csv_filename}")
    print("=" * 80)
    print("\nThe CSV includes:")
    print("  • All 8 strategies tested on same 100 words")
    print("  • Hamming distance (character position differences)")
    print("  • Levenshtein distance (edit distance)")
    print("  • All 6 guesses per game with feedback")
    print("=" * 80)


if __name__ == "__main__":
    main()
