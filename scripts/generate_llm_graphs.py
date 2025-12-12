#!/usr/bin/env python3
"""
Generate visualization graphs for LLM evaluation results.
Creates the same plots as algorithm evaluation for comparison.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from collections import defaultdict
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

def load_and_process_llm_results(results_dir):
    """Load all LLM CSV files and calculate distances."""
    all_results = []

    csv_files = list(Path(results_dir).glob('model_*.csv'))
    print(f"Loading {len(csv_files)} LLM result files...")

    for csv_file in csv_files:
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

    combined = pd.concat(all_results, ignore_index=True)
    print(f"Loaded {len(combined)} total attempts from {len(csv_files)} files")
    return combined

def plot_mean_distance_per_turn(results, distance_col, ylabel, title, output_path):
    """Plot mean distance per turn for each model+prompt combination."""
    fig, ax = plt.subplots(figsize=(12, 8))

    # Create model+prompt identifier
    results['model_prompt'] = results['model_name'] + ' (' + results['prompt_type'] + ')'

    # Calculate mean distance per turn for each model+prompt
    distance_by_turn = results.groupby(['model_prompt', 'attempt_number'])[distance_col].mean().reset_index()

    # Plot each model+prompt type
    for model_prompt in sorted(distance_by_turn['model_prompt'].unique()):
        data = distance_by_turn[distance_by_turn['model_prompt'] == model_prompt]
        ax.plot(data['attempt_number'], data[distance_col], marker='o', label=model_prompt, linewidth=2, markersize=6)

    ax.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(1, 7))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_distance_reduction_per_turn(results, distance_col, ylabel, title, output_path):
    """Plot average distance reduction per turn."""
    fig, ax = plt.subplots(figsize=(12, 8))

    results['model_prompt'] = results['model_name'] + ' (' + results['prompt_type'] + ')'

    # Calculate reduction (distance at turn N - distance at turn N+1)
    reductions = []
    for model_prompt in results['model_prompt'].unique():
        model_data = results[results['model_prompt'] == model_prompt]
        turn_distances = model_data.groupby('attempt_number')[distance_col].mean()

        for turn in range(1, 6):
            if turn in turn_distances.index and turn+1 in turn_distances.index:
                reduction = turn_distances[turn] - turn_distances[turn+1]
                reductions.append({
                    'model_prompt': model_prompt,
                    'turn': turn,
                    'reduction': reduction
                })

    reduction_df = pd.DataFrame(reductions)

    # Plot
    for model_prompt in sorted(reduction_df['model_prompt'].unique()):
        data = reduction_df[reduction_df['model_prompt'] == model_prompt]
        ax.plot(data['turn'], data['reduction'], marker='o', label=model_prompt, linewidth=2, markersize=6)

    ax.set_xlabel('Turn Number', fontsize=12, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=12, fontweight='bold')
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8)
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(1, 6))
    ax.axhline(y=0, color='gray', linestyle='--', alpha=0.5)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_avg_attempts_by_model(results, output_path):
    """Plot average attempts by model and prompt type."""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Calculate average attempts for wins only
    wins_only = results[results['win'] == True].copy()
    avg_attempts = wins_only.groupby(['model_name', 'prompt_type'])['attempt_number'].max().reset_index()
    avg_attempts = avg_attempts.groupby(['model_name', 'prompt_type'])['attempt_number'].mean().reset_index()

    # Pivot for grouped bar chart
    pivot_data = avg_attempts.pivot(index='model_name', columns='prompt_type', values='attempt_number')

    # Sort by overall average
    pivot_data['avg'] = pivot_data.mean(axis=1)
    pivot_data = pivot_data.sort_values('avg')
    pivot_data = pivot_data.drop('avg', axis=1)

    # Plot
    pivot_data.plot(kind='bar', ax=ax, width=0.8, edgecolor='black', linewidth=0.5)

    ax.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Attempts (when won)', fontsize=12, fontweight='bold')
    ax.set_title('Average Attempts by Model and Prompt Type', fontsize=14, fontweight='bold', pad=20)
    ax.legend(title='Prompt Type', fontsize=10)
    ax.grid(True, alpha=0.3, axis='y')
    plt.xticks(rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_overall_performance(results, output_path):
    """Plot overall win rate and average attempts."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    # Calculate metrics by model and prompt type
    metrics = results.groupby(['model_name', 'prompt_type']).agg({
        'win': 'mean',
        'attempt_number': lambda x: x[results.loc[x.index, 'win'] == True].max() if any(results.loc[x.index, 'win']) else 0
    }).reset_index()

    metrics['win_rate'] = metrics['win'] * 100

    # Pivot for plotting
    win_pivot = metrics.pivot(index='model_name', columns='prompt_type', values='win_rate')
    att_pivot = metrics.pivot(index='model_name', columns='prompt_type', values='attempt_number')

    # Sort by average win rate
    win_pivot['avg'] = win_pivot.mean(axis=1)
    win_pivot = win_pivot.sort_values('avg', ascending=False)
    att_pivot = att_pivot.reindex(win_pivot.index)
    win_pivot = win_pivot.drop('avg', axis=1)

    # Plot 1: Win Rate
    win_pivot.plot(kind='bar', ax=ax1, width=0.8, edgecolor='black', linewidth=0.5)
    ax1.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Win Rate by Model and Prompt Type', fontsize=14, fontweight='bold')
    ax1.legend(title='Prompt Type', fontsize=10)
    ax1.grid(True, alpha=0.3, axis='y')
    ax1.set_ylim([0, 105])
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')

    # Plot 2: Average Attempts
    att_pivot.plot(kind='bar', ax=ax2, width=0.8, edgecolor='black', linewidth=0.5)
    ax2.set_xlabel('Model', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Average Attempts', fontsize=12, fontweight='bold')
    ax2.set_title('Average Attempts by Model and Prompt Type', fontsize=14, fontweight='bold')
    ax2.legend(title='Prompt Type', fontsize=10)
    ax2.grid(True, alpha=0.3, axis='y')
    plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_distance_convergence(results, output_path):
    """Plot distance convergence patterns."""
    fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))

    # Separate by prompt type
    for prompt_type, ax_ham, ax_lev in [('cot', ax1, ax2), ('zero-shot', ax3, ax4)]:
        prompt_data = results[results['prompt_type'] == prompt_type]

        # Hamming distance
        for model in sorted(prompt_data['model_name'].unique()):
            model_data = prompt_data[prompt_data['model_name'] == model]
            ham_by_turn = model_data.groupby('attempt_number')['hamming_distance'].mean()
            ax_ham.plot(ham_by_turn.index, ham_by_turn.values, marker='o', label=model, linewidth=2, markersize=4)

        ax_ham.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
        ax_ham.set_ylabel('Mean Hamming Distance', fontsize=11, fontweight='bold')
        ax_ham.set_title(f'Hamming Distance Convergence - {prompt_type.upper()}', fontsize=12, fontweight='bold')
        ax_ham.legend(fontsize=8, loc='best')
        ax_ham.grid(True, alpha=0.3)
        ax_ham.set_xticks(range(1, 7))

        # Levenshtein distance
        for model in sorted(prompt_data['model_name'].unique()):
            model_data = prompt_data[prompt_data['model_name'] == model]
            lev_by_turn = model_data.groupby('attempt_number')['levenshtein_distance'].mean()
            ax_lev.plot(lev_by_turn.index, lev_by_turn.values, marker='o', label=model, linewidth=2, markersize=4)

        ax_lev.set_xlabel('Turn Number', fontsize=11, fontweight='bold')
        ax_lev.set_ylabel('Mean Levenshtein Distance', fontsize=11, fontweight='bold')
        ax_lev.set_title(f'Levenshtein Distance Convergence - {prompt_type.upper()}', fontsize=12, fontweight='bold')
        ax_lev.legend(fontsize=8, loc='best')
        ax_lev.grid(True, alpha=0.3)
        ax_lev.set_xticks(range(1, 7))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def plot_attempt_distribution(results, output_path):
    """Plot distribution of attempts needed to win."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

    wins_only = results[results['win'] == True].copy()

    # Get final attempt number for each game
    final_attempts = wins_only.groupby(['model_name', 'prompt_type', 'game_id'])['attempt_number'].max().reset_index()

    # Plot CoT
    cot_data = final_attempts[final_attempts['prompt_type'] == 'cot']
    for model in sorted(cot_data['model_name'].unique()):
        model_data = cot_data[cot_data['model_name'] == model]['attempt_number']
        counts = model_data.value_counts().sort_index()
        ax1.plot(counts.index, counts.values, marker='o', label=model, linewidth=2, markersize=6)

    ax1.set_xlabel('Attempts to Win', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Number of Games', fontsize=12, fontweight='bold')
    ax1.set_title('Attempt Distribution - Chain-of-Thought', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=8, loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(range(1, 7))

    # Plot Zero-Shot
    zs_data = final_attempts[final_attempts['prompt_type'] == 'zero-shot']
    for model in sorted(zs_data['model_name'].unique()):
        model_data = zs_data[zs_data['model_name'] == model]['attempt_number']
        counts = model_data.value_counts().sort_index()
        ax2.plot(counts.index, counts.values, marker='o', label=model, linewidth=2, markersize=6)

    ax2.set_xlabel('Attempts to Win', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Games', fontsize=12, fontweight='bold')
    ax2.set_title('Attempt Distribution - Zero-Shot', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=8, loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(range(1, 7))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_path.name}")

def main():
    # Set up paths
    script_dir = Path(__file__).parent
    results_dir = script_dir.parent / 'results' / 'llms'
    output_dir = results_dir / 'plots'
    output_dir.mkdir(parents=True, exist_ok=True)

    print("="*70)
    print("LLM Evaluation Visualization Generator")
    print("="*70)
    print()

    # Load results
    print("Loading and processing LLM results...")
    results = load_and_process_llm_results(results_dir)
    print()

    # Generate plots
    print("Generating plots...")
    print()

    print("1. Mean Hamming Distance Per Turn")
    plot_mean_distance_per_turn(
        results,
        'hamming_distance',
        'Mean Hamming Distance',
        'Mean Hamming Distance Per Turn',
        output_dir / 'mean_hamming_per_turn.png'
    )

    print("2. Mean Levenshtein Distance Per Turn")
    plot_mean_distance_per_turn(
        results,
        'levenshtein_distance',
        'Mean Levenshtein Distance',
        'Mean Levenshtein Distance Per Turn',
        output_dir / 'mean_levenshtein_per_turn.png'
    )

    print("3. Hamming Distance Reduction Per Turn")
    plot_distance_reduction_per_turn(
        results,
        'hamming_distance',
        'Average Hamming Reduction',
        'Average Hamming Distance Reduction Per Turn',
        output_dir / 'hamming_reduction_per_turn.png'
    )

    print("4. Levenshtein Distance Reduction Per Turn")
    plot_distance_reduction_per_turn(
        results,
        'levenshtein_distance',
        'Average Levenshtein Reduction',
        'Average Levenshtein Distance Reduction Per Turn',
        output_dir / 'levenshtein_reduction_per_turn.png'
    )

    print("5. Average Attempts by Model")
    plot_avg_attempts_by_model(results, output_dir / 'avg_attempts_by_model.png')

    print("6. Overall Performance")
    plot_overall_performance(results, output_dir / 'overall_performance.png')

    print("7. Distance Convergence")
    plot_distance_convergence(results, output_dir / 'distance_convergence.png')

    print("8. Attempt Distribution")
    plot_attempt_distribution(results, output_dir / 'attempt_distribution.png')

    print()
    print("="*70)
    print("All plots generated successfully!")
    print(f"Output directory: {output_dir}")
    print("="*70)

if __name__ == "__main__":
    main()
