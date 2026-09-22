#!/usr/bin/env python3
"""
Evaluation of True CSS (Current Solution Strategy) on the canonical 100-word test set.

Based on Lu & Boutilier (IJCAI 2011) - uses minimax regret with adversarial
witness targeting, rather than entropy-based information gain.
"""

import random
import csv
import sys
from datetime import datetime
from typing import List, Tuple
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'engines'))
sys.path.insert(0, str(Path(__file__).parent.parent / 'algorithms'))
sys.path.insert(0, str(Path(__file__).parent))

from wordle_env import WordleEnv
from css_true_strategy import CSSTrueStrategy
from test_set_loader import load_canonical_test_set


def load_word_list():
    """Load full word list from wordlist.txt (pool of possible guesses)."""
    wordlist_path = Path(__file__).parent.parent / 'wordlist' / 'wordlist.txt'
    with open(wordlist_path, 'r') as f:
        return [word.strip().upper() for word in f.readlines() if len(word.strip()) == 5]


def hamming_distance(word1: str, word2: str) -> int:
    """Calculate Hamming distance between two words."""
    return sum(c1 != c2 for c1, c2 in zip(word1, word2))


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


def run_css_true_test(word_list: List[str], test_set: List[Tuple[int, str, int]]) -> List[dict]:
    """Run True CSS strategy test and return detailed results."""
    print(f"\nTesting True CSS (Minimax Regret with Witness Targeting) on {len(test_set)} words...")
    print("This implements the CSS algorithm from Lu & Boutilier (IJCAI 2011).\n")

    results = []
    strategy_name = "css_true"

    for idx, (game_id, target_word, tier) in enumerate(test_set):
        if (idx + 1) % 10 == 0:
            print(f"  Progress: {idx + 1}/{len(test_set)} games completed...")

        env = WordleEnv(word_list)
        env.target_word = target_word
        env.attempts = 0
        env.done = False

        agent = SimpleAgent(word_list, CSSTrueStrategy(verbose=False))

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
                print(f"  Error in game {game_id} ({target_word}), attempt {attempt + 1}: {e}")
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
            'game_number': game_id,
            'target_word': target_word,
            'tier': tier,
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

    return results


def main():
    print("=" * 80)
    print("True CSS (Current Solution Strategy) Evaluation")
    print("=" * 80)
    print("\nBased on Lu & Boutilier (IJCAI 2011):")
    print("  - Uses minimax regret optimization")
    print("  - Targets adversarial witness to reduce worst-case gap")
    print("  - Different from entropy-based information gain\n")

    # Load word list
    word_list = load_word_list()
    print(f"Loaded {len(word_list)} words for candidate pool")

    # Load canonical test set
    test_set = load_canonical_test_set()
    print(f"Testing on {len(test_set)} words from canonical test set")

    # Run True CSS evaluation
    results = run_css_true_test(word_list, test_set)

    # Calculate summary statistics
    wins = sum(1 for r in results if r['won'])
    total_attempts = sum(r['attempts'] for r in results if r['won'])
    win_rate = wins / len(test_set) if test_set else 0
    avg_attempts = total_attempts / wins if wins > 0 else 0

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print(f"\n  Strategy:      True CSS (Minimax Regret + Witness Targeting)")
    print(f"  Win Rate:      {win_rate:.1%} ({wins}/{len(test_set)})")
    print(f"  Avg Attempts:  {avg_attempts:.2f} (when won)")

    # Tier breakdown
    print("\n  By Tier:")
    for tier in [1, 2, 3]:
        tier_results = [r for r in results if r['tier'] == tier]
        tier_wins = sum(1 for r in tier_results if r['won'])
        tier_total = len(tier_results)
        tier_rate = tier_wins / tier_total if tier_total > 0 else 0
        print(f"    Tier {tier}: {tier_rate:.1%} ({tier_wins}/{tier_total})")

    # Write results to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_dir = Path(__file__).parent.parent / 'results' / 'algorithms' / 'raw data'
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_filename = output_dir / f"css_true_results_{timestamp}.csv"

    headers = [
        'strategy', 'game_number', 'target_word', 'tier', 'won', 'attempts', 'total_reward',
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
        writer.writerows(results)

    print(f"\n  Results saved to: {csv_filename}")

    # Comparison table
    print("\n" + "=" * 80)
    print("COMPARISON WITH OTHER STRATEGIES")
    print("=" * 80)
    print("\n{:<25} {:>12} {:>15}".format("Strategy", "Win Rate", "Avg Attempts"))
    print("-" * 55)
    print("{:<25} {:>12} {:>15.2f}".format("True CSS (this run)", f"{win_rate:.1%}", avg_attempts))
    print("{:<25} {:>12} {:>15}".format("Original CSS (entropy)", "98.0%", "3.85"))
    print("{:<25} {:>12} {:>15}".format("MinMax (simple)", "98.0%", "3.86"))
    print("{:<25} {:>12} {:>15}".format("VOI", "99.0%", "3.96"))
    print("{:<25} {:>12} {:>15}".format("CSS_VOI_Alt", "100.0%", "3.85"))
    print("=" * 80)


if __name__ == "__main__":
    main()
