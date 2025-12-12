#!/usr/bin/env python3
"""
Generate side-by-side comparison plots: Algorithms vs LLMs
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def calculate_hamming_distance(word1, word2):
    """Calculate Hamming distance between two words."""
    return sum(c1 != c2 for c1, c2 in zip(word1, word2))

def calculate_levenshtein_distance(word1, word2):
    """Calculate Levenshtein distance between two words."""
    if len(word1) < len(word2):
        return calculate_levenshtein_distance(word2, word1)
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

def load_algorithm_results(results_dir):
    """Load algorithm results in long format."""
    csv_file = list(Path(results_dir).glob('algorithm_results_*.csv'))[0]
    df = pd.read_csv(csv_file)

    # Convert wide format to long format
    long_data = []
    for _, row in df.iterrows():
        for turn in range(1, 7):
            guess_col = f'guess_{turn}'
            hamming_col = f'hamming_{turn}'
            levenshtein_col = f'levenshtein_{turn}'

            if pd.notna(row.get(guess_col)):
                long_data.append({
                    'strategy': row['strategy'],
                    'game_number': row['game_number'],
                    'target_word': row['target_word'],
                    'attempt_number': turn,
                    'guess': row[guess_col],
                    'hamming_distance': row.get(hamming_col, 0),
                    'levenshtein_distance': row.get(levenshtein_col, 0),
                    'won': row['won'],
                    'attempts': row['attempts']
                })

    return pd.DataFrame(long_data)

def load_llm_results(results_dir):
    """Load LLM results and calculate distances."""
    all_results = []

    for csv_file in Path(results_dir).glob('model_*.csv'):
        df = pd.read_csv(csv_file)

        # Calculate distances
        df['hamming_distance'] = df.apply(
            lambda row: calculate_hamming_distance(row['guess'].upper(), row['target_word'].upper()),
            axis=1
        )
        df['levenshtein_distance'] = df.apply(
            lambda row: calculate_levenshtein_distance(row['guess'].upper(), row['target_word'].upper()),
            axis=1
        )

        all_results.append(df)

    return pd.concat(all_results, ignore_index=True)

def plot_distance_convergence_comparison(algo_results, llm_results, output_path):
    """Side-by-side distance convergence: Algorithms vs LLMs."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(18, 12))

    # Top row: Hamming distance
    # Left: Algorithms
    for strategy in sorted(algo_results['strategy'].unique()):
        data = algo_results[algo_results['strategy'] == strategy]
        ham_by_turn = data.groupby('attempt_number')['hamming_distance'].mean()
        ax1.plot(ham_by_turn.index, ham_by_turn.values, marker='o', label=strategy, linewidth=2, markersize=5)

    ax1.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Mean Hamming Distance', fontsize=11, fontweight='bold')
    ax1.set_title('ALGORITHMS: Hamming Distance Convergence', fontsize=13, fontweight='bold', pad=15)
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(range(1, 7))

    # Right: LLMs (aggregate by prompt type for readability)
    for prompt_type in ['cot', 'zero-shot']:
        data = llm_results[llm_results['prompt_type'] == prompt_type]
        ham_by_turn = data.groupby('attempt_number')['hamming_distance'].mean()
        label = 'Chain-of-Thought' if prompt_type == 'cot' else 'Zero-Shot'
        ax2.plot(ham_by_turn.index, ham_by_turn.values, marker='o', label=f'LLMs ({label})',
                linewidth=3, markersize=7)

    ax2.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Mean Hamming Distance', fontsize=11, fontweight='bold')
    ax2.set_title('LLMs: Hamming Distance Convergence', fontsize=13, fontweight='bold', pad=15)
    ax2.legend(fontsize=10, loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(range(1, 7))

    # Bottom row: Levenshtein distance
    # Left: Algorithms
    for strategy in sorted(algo_results['strategy'].unique()):
        data = algo_results[algo_results['strategy'] == strategy]
        lev_by_turn = data.groupby('attempt_number')['levenshtein_distance'].mean()
        ax3.plot(lev_by_turn.index, lev_by_turn.values, marker='o', label=strategy, linewidth=2, markersize=5)

    ax3.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Mean Levenshtein Distance', fontsize=11, fontweight='bold')
    ax3.set_title('ALGORITHMS: Levenshtein Distance Convergence', fontsize=13, fontweight='bold', pad=15)
    ax3.legend(fontsize=8, loc='best')
    ax3.grid(True, alpha=0.3)
    ax3.set_xticks(range(1, 7))

    # Right: LLMs
    for prompt_type in ['cot', 'zero-shot']:
        data = llm_results[llm_results['prompt_type'] == prompt_type]
        lev_by_turn = data.groupby('attempt_number')['levenshtein_distance'].mean()
        label = 'Chain-of-Thought' if prompt_type == 'cot' else 'Zero-Shot'
        ax4.plot(lev_by_turn.index, lev_by_turn.values, marker='o', label=f'LLMs ({label})',
                linewidth=3, markersize=7)

    ax4.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
    ax4.set_ylabel('Mean Levenshtein Distance', fontsize=11, fontweight='bold')
    ax4.set_title('LLMs: Levenshtein Distance Convergence', fontsize=13, fontweight='bold', pad=15)
    ax4.legend(fontsize=10, loc='best')
    ax4.grid(True, alpha=0.3)
    ax4.set_xticks(range(1, 7))

    plt.suptitle('Distance Convergence Comparison: Algorithms vs LLMs',
                 fontsize=16, fontweight='bold', y=0.995)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_performance_comparison(algo_results, llm_results, output_path):
    """Side-by-side performance comparison: Win rate and attempts."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # Calculate algorithm metrics
    algo_metrics = algo_results.groupby('strategy').agg({
        'won': lambda x: (x == True).mean() * 100,
        'attempts': 'mean'
    }).reset_index()
    algo_metrics.columns = ['strategy', 'win_rate', 'avg_attempts']
    algo_metrics = algo_metrics.sort_values('win_rate', ascending=False)

    # Calculate LLM metrics (by prompt type)
    llm_wins = llm_results[llm_results['win'] == True]
    llm_metrics = llm_results.groupby('prompt_type').agg({
        'win': 'mean'
    }).reset_index()
    llm_metrics['win_rate'] = llm_metrics['win'] * 100

    llm_attempts = llm_wins.groupby('prompt_type')['attempt_number'].mean().reset_index()
    llm_attempts.columns = ['prompt_type', 'avg_attempts']

    llm_metrics = llm_metrics.merge(llm_attempts, on='prompt_type')
    llm_metrics['label'] = llm_metrics['prompt_type'].map({
        'cot': 'LLMs (CoT)',
        'zero-shot': 'LLMs (Zero-Shot)'
    })

    # Plot 1: Win Rate Comparison
    x_algo = np.arange(len(algo_metrics))
    x_llm = np.arange(len(llm_metrics)) + len(algo_metrics) + 1

    ax1.bar(x_algo, algo_metrics['win_rate'], color='steelblue', edgecolor='black',
            linewidth=1, label='Algorithms', alpha=0.8)
    ax1.bar(x_llm, llm_metrics['win_rate'], color='coral', edgecolor='black',
            linewidth=1, label='LLMs', alpha=0.8)

    # Add average lines
    algo_avg = algo_metrics['win_rate'].mean()
    llm_avg = llm_metrics['win_rate'].mean()
    ax1.axhline(y=algo_avg, color='steelblue', linestyle='--', linewidth=2,
                label=f'Algo Avg: {algo_avg:.1f}%', alpha=0.7)
    ax1.axhline(y=llm_avg, color='coral', linestyle='--', linewidth=2,
                label=f'LLM Avg: {llm_avg:.1f}%', alpha=0.7)

    all_labels = list(algo_metrics['strategy']) + [''] + list(llm_metrics['label'])
    ax1.set_xticks(list(x_algo) + [len(algo_metrics)] + list(x_llm))
    ax1.set_xticklabels(all_labels, rotation=45, ha='right', fontsize=9)
    ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Win Rate Comparison', fontsize=14, fontweight='bold', pad=15)
    ax1.legend(fontsize=10, loc='lower left')
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim([0, 105])

    # Plot 2: Average Attempts Comparison
    ax2.bar(x_algo, algo_metrics['avg_attempts'], color='steelblue', edgecolor='black',
            linewidth=1, label='Algorithms', alpha=0.8)
    ax2.bar(x_llm, llm_metrics['avg_attempts'], color='coral', edgecolor='black',
            linewidth=1, label='LLMs', alpha=0.8)

    # Add average lines
    algo_avg_att = algo_metrics['avg_attempts'].mean()
    llm_avg_att = llm_metrics['avg_attempts'].mean()
    ax2.axhline(y=algo_avg_att, color='steelblue', linestyle='--', linewidth=2,
                label=f'Algo Avg: {algo_avg_att:.2f}', alpha=0.7)
    ax2.axhline(y=llm_avg_att, color='coral', linestyle='--', linewidth=2,
                label=f'LLM Avg: {llm_avg_att:.2f}', alpha=0.7)

    ax2.set_xticks(list(x_algo) + [len(algo_metrics)] + list(x_llm))
    ax2.set_xticklabels(all_labels, rotation=45, ha='right', fontsize=9)
    ax2.set_ylabel('Average Attempts (when won)', fontsize=12, fontweight='bold')
    ax2.set_title('Average Attempts Comparison', fontsize=14, fontweight='bold', pad=15)
    ax2.legend(fontsize=10, loc='upper left')
    ax2.grid(True, alpha=0.3, axis='y')

    plt.suptitle('Overall Performance: Algorithms vs LLMs', fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_turn_by_turn_comparison(algo_results, llm_results, output_path):
    """Turn-by-turn success rate comparison."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    # Calculate cumulative win rates by turn
    turns = range(1, 7)

    # Algorithms
    algo_cumulative = []
    algo_total_games = len(algo_results['game_number'].unique())

    for turn in turns:
        wins = len(algo_results[(algo_results['won'] == True) &
                                (algo_results['attempts'] <= turn)].groupby('game_number').first())
        algo_cumulative.append(wins / algo_total_games * 100)

    # LLMs (by prompt type)
    for prompt_type, color, label in [('cot', 'darkred', 'Chain-of-Thought'),
                                       ('zero-shot', 'darkblue', 'Zero-Shot')]:
        llm_data = llm_results[llm_results['prompt_type'] == prompt_type]
        llm_total_games = len(llm_data['game_id'].unique())

        llm_cumulative = []
        for turn in turns:
            # Count games won by this turn
            won_games = llm_data[(llm_data['win'] == True) &
                                (llm_data['attempt_number'] <= turn)]['game_id'].nunique()
            llm_cumulative.append(won_games / llm_total_games * 100)

        ax1.plot(turns, llm_cumulative, marker='o', linewidth=3, markersize=8,
                label=f'LLMs ({label})', color=color)

    # Plot algorithms
    ax1.plot(turns, algo_cumulative, marker='s', linewidth=3, markersize=8,
            label='Algorithms (All)', color='green', linestyle='--')

    ax1.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Cumulative Win Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Cumulative Win Rate by Turn', fontsize=14, fontweight='bold', pad=15)
    ax1.legend(fontsize=11, loc='lower right')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(turns)
    ax1.set_ylim([0, 105])

    # Per-turn win rate (win ON this turn, given reached it)
    algo_per_turn = []
    for turn in turns:
        games_at_turn = len(algo_results[algo_results['attempt_number'] == turn])
        wins_at_turn = len(algo_results[(algo_results['attempt_number'] == turn) &
                                        (algo_results['won'] == True)])
        rate = (wins_at_turn / games_at_turn * 100) if games_at_turn > 0 else 0
        algo_per_turn.append(rate)

    for prompt_type, color, label in [('cot', 'darkred', 'Chain-of-Thought'),
                                       ('zero-shot', 'darkblue', 'Zero-Shot')]:
        llm_data = llm_results[llm_results['prompt_type'] == prompt_type]

        llm_per_turn = []
        for turn in turns:
            attempts_at_turn = len(llm_data[llm_data['attempt_number'] == turn])
            wins_at_turn = len(llm_data[(llm_data['attempt_number'] == turn) &
                                        (llm_data['win'] == True)])
            rate = (wins_at_turn / attempts_at_turn * 100) if attempts_at_turn > 0 else 0
            llm_per_turn.append(rate)

        ax2.plot(turns, llm_per_turn, marker='o', linewidth=3, markersize=8,
                label=f'LLMs ({label})', color=color)

    ax2.plot(turns, algo_per_turn, marker='s', linewidth=3, markersize=8,
            label='Algorithms (All)', color='green', linestyle='--')

    ax2.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Per-Turn Success Rate (%)', fontsize=12, fontweight='bold')
    ax2.set_title('Success Rate per Turn (Win on this turn | Reached it)',
                  fontsize=14, fontweight='bold', pad=15)
    ax2.legend(fontsize=11, loc='upper left')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(turns)

    plt.suptitle('Turn-by-Turn Analysis: Algorithms vs LLMs',
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_distance_reduction_comparison(algo_results, llm_results, output_path):
    """Compare distance reduction rates per turn."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 8))

    turns = range(1, 6)  # Turns 1-5 (reduction from turn N to N+1)

    # Hamming reduction - Algorithms
    algo_ham_reduction = []
    for turn in turns:
        dist_before = algo_results[algo_results['attempt_number'] == turn]['hamming_distance'].mean()
        dist_after = algo_results[algo_results['attempt_number'] == turn + 1]['hamming_distance'].mean()
        algo_ham_reduction.append(dist_before - dist_after)

    ax1.plot(turns, algo_ham_reduction, marker='s', linewidth=3, markersize=8,
            label='Algorithms (All)', color='green', linestyle='--')

    # Hamming reduction - LLMs
    for prompt_type, color, label in [('cot', 'darkred', 'Chain-of-Thought'),
                                       ('zero-shot', 'darkblue', 'Zero-Shot')]:
        llm_data = llm_results[llm_results['prompt_type'] == prompt_type]
        llm_ham_reduction = []
        for turn in turns:
            dist_before = llm_data[llm_data['attempt_number'] == turn]['hamming_distance'].mean()
            dist_after = llm_data[llm_data['attempt_number'] == turn + 1]['hamming_distance'].mean()
            llm_ham_reduction.append(dist_before - dist_after)

        ax1.plot(turns, llm_ham_reduction, marker='o', linewidth=3, markersize=8,
                label=f'LLMs ({label})', color=color)

    ax1.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Hamming Distance Reduction', fontsize=12, fontweight='bold')
    ax1.set_title('Hamming Distance Reduction per Turn', fontsize=14, fontweight='bold', pad=15)
    ax1.legend(fontsize=11, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(turns)
    ax1.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

    # Levenshtein reduction - Algorithms
    algo_lev_reduction = []
    for turn in turns:
        dist_before = algo_results[algo_results['attempt_number'] == turn]['levenshtein_distance'].mean()
        dist_after = algo_results[algo_results['attempt_number'] == turn + 1]['levenshtein_distance'].mean()
        algo_lev_reduction.append(dist_before - dist_after)

    ax2.plot(turns, algo_lev_reduction, marker='s', linewidth=3, markersize=8,
            label='Algorithms (All)', color='green', linestyle='--')

    # Levenshtein reduction - LLMs
    for prompt_type, color, label in [('cot', 'darkred', 'Chain-of-Thought'),
                                       ('zero-shot', 'darkblue', 'Zero-Shot')]:
        llm_data = llm_results[llm_results['prompt_type'] == prompt_type]
        llm_lev_reduction = []
        for turn in turns:
            dist_before = llm_data[llm_data['attempt_number'] == turn]['levenshtein_distance'].mean()
            dist_after = llm_data[llm_data['attempt_number'] == turn + 1]['levenshtein_distance'].mean()
            llm_lev_reduction.append(dist_before - dist_after)

        ax2.plot(turns, llm_lev_reduction, marker='o', linewidth=3, markersize=8,
                label=f'LLMs ({label})', color=color)

    ax2.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Levenshtein Distance Reduction', fontsize=12, fontweight='bold')
    ax2.set_title('Levenshtein Distance Reduction per Turn', fontsize=14, fontweight='bold', pad=15)
    ax2.legend(fontsize=11, loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(turns)
    ax2.axhline(y=0, color='gray', linestyle='-', alpha=0.3)

    plt.suptitle('Distance Reduction Comparison: Algorithms vs LLMs',
                 fontsize=16, fontweight='bold', y=0.98)
    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    algo_dir = script_dir.parent / 'results' / 'algorithms'
    llm_dir = script_dir.parent / 'results' / 'llms'
    output_dir = script_dir.parent / 'results' / 'comparison_plots'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("Algorithms vs LLMs Comparison Visualizations")
    print("="*70)
    print()

    # Load data
    print("Loading algorithm results...")
    algo_results = load_algorithm_results(algo_dir)
    print(f"  Loaded {len(algo_results)} algorithm attempts")

    print("Loading LLM results...")
    llm_results = load_llm_results(llm_dir)
    print(f"  Loaded {len(llm_results)} LLM attempts")
    print()

    # Generate comparison plots
    print("Generating comparison plots...")
    print()

    print("1. Distance Convergence Comparison")
    plot_distance_convergence_comparison(algo_results, llm_results,
                                        output_dir / 'distance_convergence_comparison.png')

    print("2. Overall Performance Comparison")
    plot_performance_comparison(algo_results, llm_results,
                               output_dir / 'performance_comparison.png')

    print("3. Turn-by-Turn Analysis")
    plot_turn_by_turn_comparison(algo_results, llm_results,
                                output_dir / 'turn_by_turn_comparison.png')

    print("4. Distance Reduction Comparison")
    plot_distance_reduction_comparison(algo_results, llm_results,
                                      output_dir / 'distance_reduction_comparison.png')

    print()
    print("="*70)
    print("All comparison plots generated successfully!")
    print(f"Output directory: {output_dir}")
    print("="*70)

if __name__ == "__main__":
    main()
