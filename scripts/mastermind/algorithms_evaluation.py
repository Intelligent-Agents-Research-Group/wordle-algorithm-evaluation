"""
Mastermind Algorithms Evaluation Script.

Evaluates CSS, VOI, and Random strategies on both Classic (6 colors) and Extended (8 colors) variants.
Uses fixed test set (seed=42) for reproducibility across all conditions.
"""

import sys
import os
import json
import random
from datetime import datetime
from typing import Dict, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engines.mastermind_env import MastermindEnv
from algorithms.mastermind_css_strategy import MastermindCSSStrategy
from algorithms.mastermind_voi_strategy import MastermindVOIStrategy
from algorithms.mastermind_random_strategy import MastermindRandomStrategy
from test_set_loader import get_test_codes


def run_game(env: MastermindEnv, strategy, target: str, verbose: bool = False) -> Dict:
    """Run a single game with a fixed target and return results."""
    env.reset(target=target)  # Use fixed target
    candidates = env.get_all_candidates()
    history = []

    if hasattr(strategy, 'initialize_beliefs'):
        strategy.initialize_beliefs(candidates)

    while not env.done:
        guess = strategy.select_guess(candidates, history)

        if guess is None:
            break

        feedback, reward = env.guess(guess)
        history.append((guess, feedback))
        candidates = strategy.update_belief(candidates, guess, feedback)

        if verbose:
            print(f"  Guess {len(history)}: {guess} -> {env.feedback_to_string(feedback)} ({len(candidates)} remaining)")

    won = history[-1][0] == target if history else False

    return {
        'target': target,
        'won': won,
        'attempts': len(history),
        'history': [(g, f) for g, f in history],
        'total_reward': env.get_total_reward()
    }


def evaluate_strategy(strategy_class, strategy_name: str, variant: str, num_games: int = 100, verbose: bool = False) -> Dict:
    """Evaluate a strategy over multiple games using fixed test set."""
    env = MastermindEnv(variant=variant)
    info = env.get_info()

    # Get FIXED test set (same targets across all strategies for fair comparison)
    test_targets = get_test_codes(variant, num_games)

    results = {
        'strategy': strategy_name,
        'variant': variant,
        'num_colors': info['num_colors'],
        'search_space': info['search_space'],
        'num_games': num_games,
        'test_set_seed': 42,
        'games': [],
        'wins': 0,
        'total_attempts': 0,
        'total_reward': 0
    }

    for i, target in enumerate(test_targets):
        strategy = strategy_class(num_pegs=env.num_pegs)
        game_result = run_game(env, strategy, target, verbose=verbose)

        results['games'].append({
            'game_id': i + 1,
            'target': game_result['target'],
            'won': game_result['won'],
            'attempts': game_result['attempts'],
            'reward': game_result['total_reward']
        })

        if game_result['won']:
            results['wins'] += 1
            results['total_attempts'] += game_result['attempts']
        results['total_reward'] += game_result['total_reward']

        if (i + 1) % 20 == 0:
            print(f"  {strategy_name} ({variant}): {i + 1}/{num_games} games completed")

    results['win_rate'] = results['wins'] / num_games
    results['avg_attempts'] = results['total_attempts'] / results['wins'] if results['wins'] > 0 else 0
    results['avg_reward'] = results['total_reward'] / num_games

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Evaluate Mastermind strategies')
    parser.add_argument('--num-games', type=int, default=100, help='Number of games per strategy')
    parser.add_argument('--variant', type=str, choices=['classic', 'extended', 'both'], default='both',
                        help='Which variant to test')
    parser.add_argument('--verbose', action='store_true', help='Print detailed game output')
    parser.add_argument('--seed', type=int, default=42, help='Random seed')
    args = parser.parse_args()

    random.seed(args.seed)

    strategies = [
        (MastermindCSSStrategy, 'CSS'),
        (MastermindVOIStrategy, 'VOI'),
        (MastermindRandomStrategy, 'Random')
    ]

    variants = ['classic', 'extended'] if args.variant == 'both' else [args.variant]

    all_results = {}

    print(f"\n{'='*60}")
    print("Mastermind Strategy Evaluation")
    print(f"{'='*60}")
    print(f"Games per strategy: {args.num_games}")
    print(f"Variants: {', '.join(variants)}")
    print(f"Random seed: {args.seed}")

    for variant in variants:
        env = MastermindEnv(variant=variant)
        info = env.get_info()
        print(f"\n{'-'*60}")
        print(f"Variant: {variant.upper()}")
        print(f"Colors: {info['colors']} ({info['num_colors']} colors)")
        print(f"Search space: {info['search_space']} codes")
        print(f"{'-'*60}")

        all_results[variant] = {}

        for strategy_class, strategy_name in strategies:
            print(f"\nEvaluating {strategy_name}...")
            results = evaluate_strategy(
                strategy_class,
                strategy_name,
                variant,
                num_games=args.num_games,
                verbose=args.verbose
            )
            all_results[variant][strategy_name] = results

            print(f"  Win Rate: {results['win_rate']*100:.1f}%")
            print(f"  Avg Attempts (wins): {results['avg_attempts']:.2f}")
            print(f"  Avg Reward: {results['avg_reward']:.2f}")

    # Summary table
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")

    for variant in variants:
        print(f"\n{variant.upper()} Mastermind:")
        print(f"{'Strategy':<12} {'Win Rate':>10} {'Avg Attempts':>14} {'Avg Reward':>12}")
        print("-" * 50)

        for strategy_name in ['CSS', 'VOI', 'Random']:
            r = all_results[variant][strategy_name]
            print(f"{strategy_name:<12} {r['win_rate']*100:>9.1f}% {r['avg_attempts']:>14.2f} {r['avg_reward']:>12.2f}")

    # Save results
    results_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                               'results', 'mastermind')
    os.makedirs(results_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_file = os.path.join(results_dir, f'evaluation_{timestamp}.json')

    with open(results_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to: {results_file}")


if __name__ == '__main__':
    main()
