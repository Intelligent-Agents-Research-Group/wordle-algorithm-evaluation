"""
Canonical Test Set Loader

Shared utility for loading the canonical test set to ensure all evaluations
use identical words in identical order.
"""

import csv
from pathlib import Path
from typing import List, Tuple


def load_canonical_test_set(filepath=None) -> List[Tuple[int, str, int]]:
    """
    Load the canonical test set.

    Args:
        filepath: Path to test_set.csv (optional, auto-detected if None)

    Returns:
        List of tuples: [(game_id, word, tier), ...]

    Example:
        >>> test_set = load_canonical_test_set()
        >>> game_id, word, tier = test_set[0]
        >>> print(f"Game {game_id}: {word} (Tier {tier})")
        Game 1: PHOTO (Tier 1)
    """
    if filepath is None:
        # Auto-detect path relative to this file
        script_dir = Path(__file__).parent
        filepath = script_dir.parent / 'wordlist' / 'test_set.csv'

    filepath = Path(filepath)

    if not filepath.exists():
        raise FileNotFoundError(
            f"Canonical test set not found at: {filepath}\n"
            f"Please run: python scripts/generate_test_set.py"
        )

    test_set = []

    with open(filepath, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        for row in reader:
            game_id = int(row['game_id'])
            word = row['word'].upper()
            tier = int(row['tier'])

            test_set.append((game_id, word, tier))

    return test_set


def get_test_words_only(filepath=None) -> List[str]:
    """
    Get just the words from the canonical test set (in order).

    Args:
        filepath: Path to test_set.csv (optional)

    Returns:
        List of words in test order

    Example:
        >>> words = get_test_words_only()
        >>> print(words[:5])
        ['PHOTO', 'PARTY', 'TRICK', 'DIRTY', 'USUAL']
    """
    test_set = load_canonical_test_set(filepath)
    return [word for _, word, _ in test_set]


def print_test_set_info(filepath=None):
    """Print summary information about the canonical test set."""
    test_set = load_canonical_test_set(filepath)

    tier_counts = {}
    for _, _, tier in test_set:
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("="*60)
    print("CANONICAL TEST SET INFO")
    print("="*60)
    print(f"Total words: {len(test_set)}")
    print(f"\nWords per tier:")
    for tier in sorted(tier_counts.keys()):
        count = tier_counts[tier]
        print(f"  Tier {tier}: {count} words ({count/len(test_set)*100:.1f}%)")

    print(f"\nFirst 5 words:")
    for i in range(min(5, len(test_set))):
        game_id, word, tier = test_set[i]
        print(f"  Game {game_id}: {word} (Tier {tier})")

    print("="*60)


if __name__ == "__main__":
    # Test the loader
    print_test_set_info()
