#!/usr/bin/env python3
"""
Generate Focused Individual Graphs for Algorithm Evaluation

Creates individual, publication-quality graphs for specific metrics:
1. Mean Hamming Distance Per Turn
2. Mean Levenshtein Distance Per Turn
3. Average Attempts by Strategy
4. Average Per-Turn Hamming Reduction
5. Average Per-Turn Levenshtein Reduction

Usage:
    python generate_focused_graphs.py [results_csv_path]
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np

# Set style for publication-quality graphs
plt.style.use('seaborn-v0_8-darkgrid')
COLORS = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f']


def load_results(csv_path):
    """Load results from CSV file."""
    results = []
    with open(csv_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append(row)
    return results


def plot_mean_hamming_per_turn(results, output_dir):
    """Plot mean Hamming distance for each turn across all strategies."""
    distance_stats = defaultdict(lambda: [[] for _ in range(6)])
    
    for row in results:
        strategy = row['strategy']
        for attempt in range(1, 7):
            hamming = row.get(f'hamming_{attempt}', '')
            if hamming and hamming != '':
                try:
                    distance_stats[strategy][attempt - 1].append(int(hamming))
                except ValueError:
                    pass
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 7))
    
    strategies = sorted([s for s in distance_stats.keys() if s != 'pure_random'])
    attempts = list(range(1, 7))
    
    for i, strategy in enumerate(strategies):
        hamming_avg = [np.mean(distance_stats[strategy][j]) 
                      if distance_stats[strategy][j] else 0 
                      for j in range(6)]
        ax.plot(attempts, hamming_avg, marker='o', linewidth=3, markersize=8,
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax.set_xlabel('Turn Number', fontsize=14, fontweight='bold')
    ax.set_ylabel('Mean Hamming Distance', fontsize=14, fontweight='bold')
    ax.set_title('Mean Hamming Distance Per Turn', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1.5)
    ax.set_ylim([0, 5])
    ax.set_xticks(attempts)
    
    plt.tight_layout()
    output_path = output_dir / 'mean_hamming_per_turn.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_mean_levenshtein_per_turn(results, output_dir):
    """Plot mean Levenshtein distance for each turn across all strategies."""
    distance_stats = defaultdict(lambda: [[] for _ in range(6)])
    
    for row in results:
        strategy = row['strategy']
        for attempt in range(1, 7):
            levenshtein = row.get(f'levenshtein_{attempt}', '')
            if levenshtein and levenshtein != '':
                try:
                    distance_stats[strategy][attempt - 1].append(int(levenshtein))
                except ValueError:
                    pass
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 7))
    
    strategies = sorted([s for s in distance_stats.keys() if s != 'pure_random'])
    attempts = list(range(1, 7))
    
    for i, strategy in enumerate(strategies):
        levenshtein_avg = [np.mean(distance_stats[strategy][j])
                          if distance_stats[strategy][j] else 0
                          for j in range(6)]
        ax.plot(attempts, levenshtein_avg, marker='s', linewidth=3, markersize=8,
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax.set_xlabel('Turn Number', fontsize=14, fontweight='bold')
    ax.set_ylabel('Mean Levenshtein Distance', fontsize=14, fontweight='bold')
    ax.set_title('Mean Levenshtein Distance Per Turn', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1.5)
    ax.set_ylim([0, 5])
    ax.set_xticks(attempts)
    
    plt.tight_layout()
    output_path = output_dir / 'mean_levenshtein_per_turn.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_avg_attempts_by_strategy(results, output_dir):
    """Plot average attempts to win by strategy."""
    stats = defaultdict(lambda: {'wins': 0, 'total': 0, 'attempts': []})
    
    for row in results:
        strategy = row['strategy']
        stats[strategy]['total'] += 1
        if row['won'] == 'True':
            stats[strategy]['wins'] += 1
            stats[strategy]['attempts'].append(int(row['attempts']))
    
    # Prepare data
    strategies = sorted([s for s in stats.keys() if s != 'pure_random'])
    avg_attempts = [np.mean(stats[s]['attempts']) if stats[s]['attempts'] else 0 for s in strategies]
    
    # Create plot
    fig, ax = plt.subplots(figsize=(12, 7))
    
    bars = ax.bar(range(len(strategies)), avg_attempts, color=COLORS[:len(strategies)], 
                  alpha=0.8, edgecolor='black', linewidth=1.5)
    
    ax.set_xlabel('Strategy', fontsize=14, fontweight='bold')
    ax.set_ylabel('Average Attempts to Win', fontsize=14, fontweight='bold')
    ax.set_title('Average Attempts by Strategy', fontsize=16, fontweight='bold', pad=20)
    ax.set_xticks(range(len(strategies)))
    ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=11)
    ax.set_ylim([0, max(avg_attempts) * 1.15])
    ax.grid(axis='y', alpha=0.3, linewidth=1.5)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, avg_attempts)):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    
    plt.tight_layout()
    output_path = output_dir / 'avg_attempts_by_strategy.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_hamming_reduction_per_turn(results, output_dir):
    """Plot average Hamming distance reduction per turn."""
    distance_stats = defaultdict(lambda: [[] for _ in range(6)])
    
    for row in results:
        strategy = row['strategy']
        for attempt in range(1, 7):
            hamming = row.get(f'hamming_{attempt}', '')
            if hamming and hamming != '':
                try:
                    distance_stats[strategy][attempt - 1].append(int(hamming))
                except ValueError:
                    pass
    
    # Calculate reductions (distance at turn N - distance at turn N+1)
    fig, ax = plt.subplots(figsize=(12, 7))
    
    strategies = sorted([s for s in distance_stats.keys() if s != 'pure_random'])
    turns = list(range(1, 6))  # Turns 1-5 (reduction from turn N to N+1)
    
    for i, strategy in enumerate(strategies):
        hamming_avg = [np.mean(distance_stats[strategy][j]) 
                      if distance_stats[strategy][j] else 0 
                      for j in range(6)]
        
        # Calculate reduction per turn
        reductions = [hamming_avg[j] - hamming_avg[j+1] for j in range(5)]
        
        ax.plot(turns, reductions, marker='o', linewidth=3, markersize=8,
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax.set_xlabel('Turn Number', fontsize=14, fontweight='bold')
    ax.set_ylabel('Average Hamming Distance Reduction', fontsize=14, fontweight='bold')
    ax.set_title('Average Per-Turn Hamming Distance Reduction', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1.5)
    ax.set_xticks(turns)
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    plt.tight_layout()
    output_path = output_dir / 'hamming_reduction_per_turn.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_levenshtein_reduction_per_turn(results, output_dir):
    """Plot average Levenshtein distance reduction per turn."""
    distance_stats = defaultdict(lambda: [[] for _ in range(6)])
    
    for row in results:
        strategy = row['strategy']
        for attempt in range(1, 7):
            levenshtein = row.get(f'levenshtein_{attempt}', '')
            if levenshtein and levenshtein != '':
                try:
                    distance_stats[strategy][attempt - 1].append(int(levenshtein))
                except ValueError:
                    pass
    
    # Calculate reductions
    fig, ax = plt.subplots(figsize=(12, 7))
    
    strategies = sorted([s for s in distance_stats.keys() if s != 'pure_random'])
    turns = list(range(1, 6))  # Turns 1-5
    
    for i, strategy in enumerate(strategies):
        levenshtein_avg = [np.mean(distance_stats[strategy][j])
                          if distance_stats[strategy][j] else 0
                          for j in range(6)]
        
        # Calculate reduction per turn
        reductions = [levenshtein_avg[j] - levenshtein_avg[j+1] for j in range(5)]
        
        ax.plot(turns, reductions, marker='s', linewidth=3, markersize=8,
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax.set_xlabel('Turn Number', fontsize=14, fontweight='bold')
    ax.set_ylabel('Average Levenshtein Distance Reduction', fontsize=14, fontweight='bold')
    ax.set_title('Average Per-Turn Levenshtein Distance Reduction', fontsize=16, fontweight='bold', pad=20)
    ax.legend(fontsize=11, loc='upper right', framealpha=0.9)
    ax.grid(True, alpha=0.3, linewidth=1.5)
    ax.set_xticks(turns)
    ax.axhline(y=0, color='red', linestyle='--', linewidth=1.5, alpha=0.5)
    
    plt.tight_layout()
    output_path = output_dir / 'levenshtein_reduction_per_turn.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


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
            print("Error: No algorithm_results CSV files found in results/algorithms/")
            return 1
        
        csv_path = csv_files[0]
    
    if not csv_path.exists():
        print(f"Error: File not found: {csv_path}")
        return 1
    
    # Determine output directory
    output_dir = csv_path.parent / 'plots'
    output_dir.mkdir(exist_ok=True)
    
    print(f"Loading results from: {csv_path}")
    results = load_results(csv_path)
    print(f"Loaded {len(results)} result rows")
    print(f"Output directory: {output_dir}\n")
    
    # Generate all plots
    print("Generating focused graphs...")
    plot_mean_hamming_per_turn(results, output_dir)
    plot_mean_levenshtein_per_turn(results, output_dir)
    plot_avg_attempts_by_strategy(results, output_dir)
    plot_hamming_reduction_per_turn(results, output_dir)
    plot_levenshtein_reduction_per_turn(results, output_dir)
    
    print("\n" + "="*80)
    print("✓ All focused graphs generated successfully!")
    print("="*80)
    print(f"\nGraphs saved to: {output_dir}")
    print("\nGenerated files:")
    print("  1. mean_hamming_per_turn.png - Mean Hamming distance for each turn")
    print("  2. mean_levenshtein_per_turn.png - Mean Levenshtein distance for each turn")
    print("  3. avg_attempts_by_strategy.png - Average attempts to win by strategy")
    print("  4. hamming_reduction_per_turn.png - Average Hamming reduction per turn")
    print("  5. levenshtein_reduction_per_turn.png - Average Levenshtein reduction per turn")
    print("="*80)


if __name__ == "__main__":
    sys.exit(main())
