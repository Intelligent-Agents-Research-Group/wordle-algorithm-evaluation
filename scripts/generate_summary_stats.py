#!/usr/bin/env python3
"""
Generate Summary Statistics for Algorithm Evaluation Results

Reads algorithm_results CSV files and generates comprehensive summary statistics
including overall performance, tier-based analysis, and distance convergence.

Usage:
    python generate_summary_stats.py [results_csv_path]

If no path is provided, uses the most recent algorithm_results file in results/
"""

import csv
import json
import sys
from pathlib import Path
from collections import defaultdict
from datetime import datetime


def load_results(csv_path):
    """Load results from CSV file."""
    results = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def calculate_overall_stats(results):
    """Calculate overall statistics by strategy."""
    strategy_stats = defaultdict(lambda: {
        'total_games': 0,
        'wins': 0,
        'losses': 0,
        'total_attempts': 0,
        'attempt_counts': []
    })

    for row in results:
        strategy = row['strategy']
        stats = strategy_stats[strategy]

        stats['total_games'] += 1

        if row['won'] == 'True':
            stats['wins'] += 1
            attempts = int(row['attempts'])
            stats['total_attempts'] += attempts
            stats['attempt_counts'].append(attempts)
        else:
            stats['losses'] += 1

    # Calculate derived metrics
    summary = {}
    for strategy, stats in strategy_stats.items():
        win_rate = stats['wins'] / stats['total_games'] if stats['total_games'] > 0 else 0
        avg_attempts = stats['total_attempts'] / stats['wins'] if stats['wins'] > 0 else 0

        summary[strategy] = {
            'total_games': stats['total_games'],
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': round(win_rate * 100, 2),
            'avg_attempts': round(avg_attempts, 2),
            'min_attempts': min(stats['attempt_counts']) if stats['attempt_counts'] else 0,
            'max_attempts': max(stats['attempt_counts']) if stats['attempt_counts'] else 0
        }

    return summary


def calculate_tier_stats(results):
    """Calculate performance broken down by word tier."""
    tier_stats = defaultdict(lambda: defaultdict(lambda: {
        'total_games': 0,
        'wins': 0,
        'total_attempts': 0
    }))

    for row in results:
        strategy = row['strategy']
        tier = int(row['tier'])
        stats = tier_stats[strategy][tier]

        stats['total_games'] += 1

        if row['won'] == 'True':
            stats['wins'] += 1
            stats['total_attempts'] += int(row['attempts'])

    # Calculate derived metrics
    summary = {}
    for strategy, tiers in tier_stats.items():
        summary[strategy] = {}
        for tier, stats in tiers.items():
            win_rate = stats['wins'] / stats['total_games'] if stats['total_games'] > 0 else 0
            avg_attempts = stats['total_attempts'] / stats['wins'] if stats['wins'] > 0 else 0

            summary[strategy][f'tier_{tier}'] = {
                'total_games': stats['total_games'],
                'wins': stats['wins'],
                'win_rate': round(win_rate * 100, 2),
                'avg_attempts': round(avg_attempts, 2)
            }

    return summary


def calculate_distance_stats(results):
    """Calculate average distance convergence patterns."""
    distance_stats = defaultdict(lambda: {
        'hamming': [[] for _ in range(6)],
        'levenshtein': [[] for _ in range(6)]
    })

    for row in results:
        strategy = row['strategy']
        stats = distance_stats[strategy]

        for attempt in range(1, 7):
            hamming = row.get(f'hamming_{attempt}', '')
            levenshtein = row.get(f'levenshtein_{attempt}', '')

            if hamming and hamming != '':
                try:
                    stats['hamming'][attempt - 1].append(int(hamming))
                except ValueError:
                    pass

            if levenshtein and levenshtein != '':
                try:
                    stats['levenshtein'][attempt - 1].append(int(levenshtein))
                except ValueError:
                    pass

    # Calculate averages
    summary = {}
    for strategy, stats in distance_stats.items():
        summary[strategy] = {
            'hamming_avg': [],
            'levenshtein_avg': []
        }

        for attempt in range(6):
            hamming_vals = stats['hamming'][attempt]
            levenshtein_vals = stats['levenshtein'][attempt]

            hamming_avg = sum(hamming_vals) / len(hamming_vals) if hamming_vals else 0
            levenshtein_avg = sum(levenshtein_vals) / len(levenshtein_vals) if levenshtein_vals else 0

            summary[strategy]['hamming_avg'].append(round(hamming_avg, 2))
            summary[strategy]['levenshtein_avg'].append(round(levenshtein_avg, 2))

    return summary


def generate_summary_report(csv_path, output_dir):
    """Generate comprehensive summary statistics."""
    print(f"Loading results from: {csv_path}")
    results = load_results(csv_path)
    print(f"Loaded {len(results)} result rows")

    # Calculate all statistics
    overall_stats = calculate_overall_stats(results)
    tier_stats = calculate_tier_stats(results)
    distance_stats = calculate_distance_stats(results)

    # Create summary object
    summary = {
        'metadata': {
            'source_file': str(csv_path),
            'total_rows': len(results),
            'generated_at': datetime.now().isoformat(),
            'strategies_evaluated': list(overall_stats.keys())
        },
        'overall_performance': overall_stats,
        'tier_performance': tier_stats,
        'distance_convergence': distance_stats
    }

    # Save as JSON
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    json_path = output_dir / f"summary_stats_{timestamp}.json"

    with open(json_path, 'w') as f:
        json.dump(summary, f, indent=2)

    print(f"\n✓ Summary statistics saved to: {json_path}")

    # Also save as readable text
    txt_path = output_dir / f"summary_stats_{timestamp}.txt"
    with open(txt_path, 'w') as f:
        f.write("="*80 + "\n")
        f.write("ALGORITHM EVALUATION SUMMARY STATISTICS\n")
        f.write("="*80 + "\n\n")

        f.write(f"Source: {csv_path.name}\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("="*80 + "\n")
        f.write("OVERALL PERFORMANCE\n")
        f.write("="*80 + "\n\n")

        f.write(f"{'Strategy':<25} {'Win Rate':>10} {'Wins/Total':>12} {'Avg Attempts':>15}\n")
        f.write("-"*80 + "\n")

        for strategy in sorted(overall_stats.keys()):
            stats = overall_stats[strategy]
            f.write(f"{strategy:<25} {stats['win_rate']:>9.1f}% "
                   f"{stats['wins']:>5}/{stats['total_games']:<5} "
                   f"{stats['avg_attempts']:>15.2f}\n")

        f.write("\n" + "="*80 + "\n")
        f.write("PERFORMANCE BY TIER\n")
        f.write("="*80 + "\n\n")

        for strategy in sorted(tier_stats.keys()):
            f.write(f"\n{strategy}:\n")
            f.write(f"  {'Tier':<10} {'Win Rate':>10} {'Wins/Total':>12} {'Avg Attempts':>15}\n")
            f.write("  " + "-"*60 + "\n")

            for tier in [1, 2, 3]:
                tier_key = f'tier_{tier}'
                if tier_key in tier_stats[strategy]:
                    stats = tier_stats[strategy][tier_key]
                    f.write(f"  {tier_key:<10} {stats['win_rate']:>9.1f}% "
                           f"{stats['wins']:>5}/{stats['total_games']:<5} "
                           f"{stats['avg_attempts']:>15.2f}\n")

        f.write("\n" + "="*80 + "\n")
        f.write("DISTANCE CONVERGENCE (Average by Attempt)\n")
        f.write("="*80 + "\n\n")

        for strategy in sorted(distance_stats.keys()):
            f.write(f"\n{strategy}:\n")
            f.write(f"  {'Attempt':<10} {'Hamming':>10} {'Levenshtein':>15}\n")
            f.write("  " + "-"*40 + "\n")

            for attempt in range(1, 7):
                hamming = distance_stats[strategy]['hamming_avg'][attempt - 1]
                levenshtein = distance_stats[strategy]['levenshtein_avg'][attempt - 1]
                f.write(f"  {attempt:<10} {hamming:>10.2f} {levenshtein:>15.2f}\n")

        f.write("\n" + "="*80 + "\n")

    print(f"✓ Readable summary saved to: {txt_path}")

    return summary


def main():
    """Main entry point."""
    # Determine input file
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        # Find most recent algorithm_results file
        results_dir = Path(__file__).parent.parent / 'results' / 'algorithms'
        csv_files = sorted(results_dir.glob('algorithm_results_*.csv'), reverse=True)

        if not csv_files:
            print("Error: No algorithm_results CSV files found in results/")
            return 1

        csv_path = csv_files[0]

    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1

    # Determine output directory
    output_dir = csv_path.parent

    # Generate summary
    summary = generate_summary_report(csv_path, output_dir)

    # Print quick summary to console
    print("\n" + "="*80)
    print("QUICK SUMMARY")
    print("="*80 + "\n")

    print(f"{'Strategy':<25} {'Win Rate':>10} {'Avg Attempts':>15}")
    print("-"*80)

    for strategy in sorted(summary['overall_performance'].keys()):
        stats = summary['overall_performance'][strategy]
        print(f"{strategy:<25} {stats['win_rate']:>9.1f}% {stats['avg_attempts']:>15.2f}")

    print("\n" + "="*80)


if __name__ == "__main__":
    sys.exit(main())
