"""
Fixed Test Set for Mastermind Experiments.

Ensures all configurations use the same target codes for fair comparison.
Uses deterministic seeding to generate reproducible test sets.
"""

import random
from itertools import product
from typing import List

# Color sets
COLORS_CLASSIC = "RGBYOW"  # 6 colors
COLORS_EXTENDED = "RGBYOWPK"  # 8 colors


def generate_all_codes(colors: str, num_pegs: int = 4) -> List[str]:
    """Generate all possible codes for a given color set."""
    return [''.join(p) for p in product(colors, repeat=num_pegs)]


def generate_test_set(variant: str, num_targets: int = 100, seed: int = 42) -> List[str]:
    """
    Generate a deterministic test set for a Mastermind variant.

    Args:
        variant: 'classic' or 'extended'
        num_targets: Number of target codes to generate
        seed: Random seed for reproducibility

    Returns:
        List of target codes (deterministic for given seed)
    """
    colors = COLORS_CLASSIC if variant == 'classic' else COLORS_EXTENDED
    all_codes = generate_all_codes(colors)

    # Use deterministic seeding
    rng = random.Random(seed)

    # Sample without replacement
    if num_targets > len(all_codes):
        raise ValueError(f"Requested {num_targets} targets but only {len(all_codes)} codes exist")

    return rng.sample(all_codes, num_targets)


def get_test_codes(variant: str, num_games: int = 100) -> List[str]:
    """
    Get the canonical test set for experiments.

    Always uses seed=42 for reproducibility across all experimental conditions.
    """
    return generate_test_set(variant, num_targets=num_games, seed=42)


# Pre-generated test sets for quick access
_TEST_SET_CACHE = {}


def get_cached_test_codes(variant: str, num_games: int = 100) -> List[str]:
    """Get test codes with caching."""
    key = (variant, num_games)
    if key not in _TEST_SET_CACHE:
        _TEST_SET_CACHE[key] = get_test_codes(variant, num_games)
    return _TEST_SET_CACHE[key]


if __name__ == "__main__":
    # Print sample test sets for verification
    for variant in ['classic', 'extended']:
        codes = get_test_codes(variant, num_games=10)
        print(f"\n{variant.upper()} test set (first 10):")
        for i, code in enumerate(codes, 1):
            print(f"  {i}: {code}")

    # Verify reproducibility
    print("\nReproducibility check:")
    set1 = get_test_codes('classic', 100)
    set2 = get_test_codes('classic', 100)
    print(f"  Sets identical: {set1 == set2}")
