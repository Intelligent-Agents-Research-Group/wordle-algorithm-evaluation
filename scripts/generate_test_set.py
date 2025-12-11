#!/usr/bin/env python3
"""
Generate Canonical Test Set for Wordle Evaluations

Creates a standardized test set of 100 words to ensure all algorithms
and LLMs are tested on identical words in identical order.

This ensures fair comparison and enables paired statistical testing.

Usage:
    python generate_test_set.py

Output:
    wordlist/test_set.csv - 100 words with tier labels
"""

import random
import csv
from pathlib import Path


def load_tiered_wordlist(filepath='../wordlist/tiered_wordlist.txt'):
    """
    Load words from tiered word list, organized by tier.

    Returns:
        dict: {tier_number: [list of words]}
    """
    tiers = {1: [], 2: [], 3: [], 4: []}
    current_tier = None

    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # Skip empty lines and total count
            if not line or line.startswith('# Total'):
                continue

            # Detect tier markers
            if line.startswith('# Tier'):
                tier_num = int(line.split()[-1])
                current_tier = tier_num
                continue

            # Skip other comments
            if line.startswith('#'):
                continue

            # Add word to current tier
            if current_tier is not None:
                tiers[current_tier].append(line.upper())

    return tiers


def generate_test_set(tiers, total_words=100, seed=42):
    """
    Generate canonical test set by sampling words from available tiers.

    Args:
        tiers: dict of {tier_number: [words]}
        total_words: total number of words in test set
        seed: random seed for reproducibility

    Returns:
        list of tuples: [(game_id, word, tier), ...]
    """
    random.seed(seed)

    # Filter out empty tiers
    available_tiers = {t: words for t, words in tiers.items() if len(words) > 0}

    if not available_tiers:
        raise ValueError("No tiers with words available")

    # Calculate words per tier (distribute evenly)
    num_tiers = len(available_tiers)
    words_per_tier = total_words // num_tiers
    remainder = total_words % num_tiers

    print(f"\nDistributing {total_words} words across {num_tiers} tiers:")
    print(f"  Base: {words_per_tier} words per tier")
    if remainder > 0:
        print(f"  Extra: {remainder} word(s) in first tier(s)")

    test_set = []
    game_id = 1

    # Sample from each available tier
    for idx, tier in enumerate(sorted(available_tiers.keys())):
        tier_words = available_tiers[tier]

        # First tier(s) get extra words if there's a remainder
        num_words = words_per_tier + (1 if idx < remainder else 0)

        if len(tier_words) < num_words:
            raise ValueError(
                f"Tier {tier} has only {len(tier_words)} words, "
                f"need {num_words}"
            )

        # Random sample without replacement
        sampled_words = random.sample(tier_words, num_words)

        # Add to test set with game IDs
        for word in sampled_words:
            test_set.append((game_id, word, tier))
            game_id += 1

        print(f"  Tier {tier}: {num_words} words sampled from {len(tier_words)} available")

    return test_set


def save_test_set(test_set, output_path='canonical_test_set.csv'):
    """Save test set to CSV file."""
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)

        # Header
        writer.writerow(['game_id', 'word', 'tier'])

        # Data
        for game_id, word, tier in test_set:
            writer.writerow([game_id, word, tier])

    print(f"✓ Canonical test set saved to: {output_path}")


def print_summary(test_set):
    """Print summary statistics of the test set."""
    tier_counts = {1: 0, 2: 0, 3: 0, 4: 0}

    for _, _, tier in test_set:
        tier_counts[tier] += 1

    print("\n" + "="*60)
    print("CANONICAL TEST SET SUMMARY")
    print("="*60)
    print(f"Total words: {len(test_set)}")
    print(f"Seed: 42 (for reproducibility)")
    print("\nWords per tier:")
    for tier in sorted(tier_counts.keys()):
        count = tier_counts[tier]
        print(f"  Tier {tier}: {count} words")

    print("\nFirst 10 games:")
    for i in range(min(10, len(test_set))):
        game_id, word, tier = test_set[i]
        print(f"  Game {game_id:3d}: {word:8s} (Tier {tier})")

    print("\nLast 10 games:")
    for i in range(max(0, len(test_set) - 10), len(test_set)):
        game_id, word, tier = test_set[i]
        print(f"  Game {game_id:3d}: {word:8s} (Tier {tier})")

    print("="*60)


def main():
    print("Generating Canonical Test Set for Wordle Evaluations")
    print("="*60)

    # Determine paths
    script_dir = Path(__file__).parent
    wordlist_path = script_dir.parent / 'wordlist' / 'tiered_wordlist.txt'
    output_path = script_dir.parent / 'wordlist' / 'test_set.csv'

    print(f"Loading tiered word list from: {wordlist_path}")

    # Load tiered words
    tiers = load_tiered_wordlist(wordlist_path)

    print(f"Loaded words:")
    for tier, words in sorted(tiers.items()):
        print(f"  Tier {tier}: {len(words)} words")

    # Generate test set
    print(f"\nGenerating test set (100 total words, seed=42)...")
    test_set = generate_test_set(tiers, total_words=100, seed=42)

    # Save to CSV
    save_test_set(test_set, output_path)

    # Print summary
    print_summary(test_set)

    print(f"\n✅ Canonical test set ready!")
    print(f"   File: {output_path}")
    print(f"   All evaluations should use this exact set for fair comparison.")


if __name__ == "__main__":
    main()
