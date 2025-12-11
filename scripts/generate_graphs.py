#!/usr/bin/env python3
"""
Generate Visualization Graphs for Algorithm Evaluation Results

Creates publication-quality graphs showing:
- Overall performance comparison (win rate, avg attempts)
- Performance by word tier (difficulty analysis)
- Distance convergence patterns (Hamming and Levenshtein)
- Attempt distribution analysis

Usage:
    python generate_graphs.py [results_csv_path]

If no path is provided, uses the most recent algorithm_results file in results/algorithms/
"""

import csv
import sys
from pathlib import Path
from collections import defaultdict
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
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


def plot_overall_performance(results, output_dir):
    """Create bar charts for overall win rate and average attempts."""
    # Calculate statistics
    stats = defaultdict(lambda: {'wins': 0, 'total': 0, 'attempts': []})
    
    for row in results:
        strategy = row['strategy']
        stats[strategy]['total'] += 1
        if row['won'] == 'True':
            stats[strategy]['wins'] += 1
            stats[strategy]['attempts'].append(int(row['attempts']))
    
    # Prepare data
    strategies = sorted([s for s in stats.keys() if s != 'pure_random'])
    win_rates = [stats[s]['wins'] / stats[s]['total'] * 100 for s in strategies]
    avg_attempts = [np.mean(stats[s]['attempts']) if stats[s]['attempts'] else 0 for s in strategies]
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    # Plot 1: Win Rate
    bars1 = ax1.bar(range(len(strategies)), win_rates, color=COLORS[:len(strategies)], alpha=0.8)
    ax1.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Win Rate by Strategy (100 games)', fontsize=14, fontweight='bold')
    ax1.set_xticks(range(len(strategies)))
    ax1.set_xticklabels(strategies, rotation=45, ha='right')
    ax1.set_ylim([0, 105])
    ax1.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars1, win_rates)):
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    # Plot 2: Average Attempts
    bars2 = ax2.bar(range(len(strategies)), avg_attempts, color=COLORS[:len(strategies)], alpha=0.8)
    ax2.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Attempts to Win', fontsize=12, fontweight='bold')
    ax2.set_title('Average Attempts by Strategy (wins only)', fontsize=14, fontweight='bold')
    ax2.set_xticks(range(len(strategies)))
    ax2.set_xticklabels(strategies, rotation=45, ha='right')
    ax2.set_ylim([0, max(avg_attempts) * 1.2])
    ax2.grid(axis='y', alpha=0.3)
    
    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars2, avg_attempts)):
        height = bar.get_height()
        ax2.text(bar.get_x() + bar.get_width()/2., height + 0.05,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    
    plt.tight_layout()
    output_path = output_dir / 'overall_performance.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_tier_performance(results, output_dir):
    """Create grouped bar charts showing performance by tier."""
    # Calculate tier statistics
    tier_stats = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'total': 0, 'attempts': []}))
    
    for row in results:
        strategy = row['strategy']
        if strategy == 'pure_random':
            continue
        tier = int(row['tier'])
        tier_stats[strategy][tier]['total'] += 1
        if row['won'] == 'True':
            tier_stats[strategy][tier]['wins'] += 1
            tier_stats[strategy][tier]['attempts'].append(int(row['attempts']))
    
    strategies = sorted(tier_stats.keys())
    tiers = [1, 2, 3]
    
    # Prepare data
    win_rates = {tier: [] for tier in tiers}
    avg_attempts = {tier: [] for tier in tiers}
    
    for strategy in strategies:
        for tier in tiers:
            stats = tier_stats[strategy][tier]
            wr = stats['wins'] / stats['total'] * 100 if stats['total'] > 0 else 0
            avg = np.mean(stats['attempts']) if stats['attempts'] else 0
            win_rates[tier].append(wr)
            avg_attempts[tier].append(avg)
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    x = np.arange(len(strategies))
    width = 0.25
    
    # Plot 1: Win Rate by Tier
    for i, tier in enumerate(tiers):
        offset = (i - 1) * width
        bars = ax1.bar(x + offset, win_rates[tier], width, 
                      label=f'Tier {tier}', alpha=0.8)
    
    ax1.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Win Rate by Strategy and Word Tier', fontsize=14, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(strategies, rotation=45, ha='right')
    ax1.legend(title='Word Tier', fontsize=10)
    ax1.set_ylim([0, 105])
    ax1.grid(axis='y', alpha=0.3)
    
    # Plot 2: Average Attempts by Tier
    for i, tier in enumerate(tiers):
        offset = (i - 1) * width
        bars = ax2.bar(x + offset, avg_attempts[tier], width,
                      label=f'Tier {tier}', alpha=0.8)
    
    ax2.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Attempts to Win', fontsize=12, fontweight='bold')
    ax2.set_title('Average Attempts by Strategy and Word Tier', fontsize=14, fontweight='bold')
    ax2.set_xticks(x)
    ax2.set_xticklabels(strategies, rotation=45, ha='right')
    ax2.legend(title='Word Tier', fontsize=10)
    ax2.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    output_path = output_dir / 'tier_performance.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_distance_convergence(results, output_dir):
    """Create line plots showing distance convergence over attempts."""
    # Calculate average distances per attempt
    distance_stats = defaultdict(lambda: {
        'hamming': [[] for _ in range(6)],
        'levenshtein': [[] for _ in range(6)]
    })
    
    for row in results:
        strategy = row['strategy']
        for attempt in range(1, 7):
            hamming = row.get(f'hamming_{attempt}', '')
            levenshtein = row.get(f'levenshtein_{attempt}', '')
            
            if hamming and hamming != '':
                try:
                    distance_stats[strategy]['hamming'][attempt - 1].append(int(hamming))
                except ValueError:
                    pass
            
            if levenshtein and levenshtein != '':
                try:
                    distance_stats[strategy]['levenshtein'][attempt - 1].append(int(levenshtein))
                except ValueError:
                    pass
    
    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
    
    strategies = sorted([s for s in distance_stats.keys() if s != 'pure_random'])
    attempts = list(range(1, 7))
    
    # Plot 1: Hamming Distance
    for i, strategy in enumerate(strategies):
        hamming_avg = [np.mean(distance_stats[strategy]['hamming'][j]) 
                      if distance_stats[strategy]['hamming'][j] else 0 
                      for j in range(6)]
        ax1.plot(attempts, hamming_avg, marker='o', linewidth=2, 
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax1.set_xlabel('Attempt Number', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Average Hamming Distance', fontsize=12, fontweight='bold')
    ax1.set_title('Hamming Distance Convergence', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=9, loc='upper right')
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim([0, 5])
    ax1.set_xticks(attempts)
    
    # Plot 2: Levenshtein Distance
    for i, strategy in enumerate(strategies):
        levenshtein_avg = [np.mean(distance_stats[strategy]['levenshtein'][j])
                          if distance_stats[strategy]['levenshtein'][j] else 0
                          for j in range(6)]
        ax2.plot(attempts, levenshtein_avg, marker='o', linewidth=2,
                label=strategy, color=COLORS[i % len(COLORS)], alpha=0.8)
    
    ax2.set_xlabel('Attempt Number', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Levenshtein Distance', fontsize=12, fontweight='bold')
    ax2.set_title('Levenshtein Distance Convergence', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=9, loc='upper right')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim([0, 5])
    ax2.set_xticks(attempts)
    
    plt.tight_layout()
    output_path = output_dir / 'distance_convergence.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"✓ Saved: {output_path}")
    plt.close()


def plot_attempt_distribution(results, output_dir):
    """Create box plot showing distribution of attempts to win."""
    # Collect attempt counts
    attempt_data = defaultdict(list)
    
    for row in results:
        strategy = row['strategy']
        if strategy == 'pure_random':
            continue
        if row['won'] == 'True':
            attempt_data[strategy].append(int(row['attempts']))
    
    strategies = sorted(attempt_data.keys())
    data = [attempt_data[s] for s in strategies]
    
    # Create box plot
    fig, ax = plt.subplots(figsize=(14, 6))
    
    bp = ax.boxplot(data, labels=strategies, patch_artist=True,
                    notch=True, showmeans=True,
                    meanprops=dict(marker='D', markerfacecolor='red', markersize=8))
    
    # Color the boxes
    for patch, color in zip(bp['boxes'], COLORS[:len(strategies)]):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
    
    ax.set_xlabel('Strategy', fontsize=12, fontweight='bold')
    ax.set_ylabel('Number of Attempts to Win', fontsize=12, fontweight='bold')
    ax.set_title('Distribution of Attempts to Win (Box Plot)', fontsize=14, fontweight='bold')
    ax.set_xticklabels(strategies, rotation=45, ha='right')
    ax.grid(axis='y', alpha=0.3)
    ax.set_ylim([0, 7])
    
    # Add legend
    red_diamond = mpatches.Patch(color='red', label='Mean')
    ax.legend(handles=[red_diamond], loc='upper right')
    
    plt.tight_layout()
    output_path = output_dir / 'attempt_distribution.png'
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
    print("Generating graphs...")
    plot_overall_performance(results, output_dir)
    plot_tier_performance(results, output_dir)
    plot_distance_convergence(results, output_dir)
    plot_attempt_distribution(results, output_dir)
    
    print("\n" + "="*80)
    print("✓ All graphs generated successfully!")
    print("="*80)
    print(f"\nGraphs saved to: {output_dir}")
    print("\nGenerated files:")
    print("  1. overall_performance.png - Win rate and average attempts comparison")
    print("  2. tier_performance.png - Performance breakdown by word difficulty tier")
    print("  3. distance_convergence.png - Hamming and Levenshtein distance over attempts")
    print("  4. attempt_distribution.png - Distribution of attempts to win (box plot)")
    print("="*80)


if __name__ == "__main__":
    sys.exit(main())
