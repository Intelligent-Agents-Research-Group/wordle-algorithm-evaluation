#!/usr/bin/env python3
"""
Create visualization of convergence trajectories across all experiment categories.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

def create_convergence_plots():
    """Create comprehensive convergence visualization."""

    # Data from analysis
    data = {
        'Pure Algorithms': {
            'hamming': [4.5275, 3.5638, 2.1658, 1.3143, 1.9321, 3.0189],
            'levenshtein': [4.4725, 3.4888, 2.1260, 1.3076, 1.9179, 2.9874],
            'n_games': 800
        },
        'Hybrids (Zero-shot)': {
            'hamming': [4.5304, 3.5138, 2.1149, 0.9780, 0.6793, 0.4511],
            'levenshtein': [4.4556, 3.4323, 2.0690, 0.9725, 0.6741, 0.4511],
            'n_games': 2700
        },
        'Hybrids (CoT)': {
            'hamming': [4.6214, 3.6921, 2.1882, 1.0060, 0.6117, 0.3904],
            'levenshtein': [4.5714, 3.6163, 2.1426, 0.9957, 0.6070, 0.3904],
            'n_games': 2703
        }
    }

    # LLM Search Space Data
    llm_data = {
        'Chain-of-Thought': {
            'candidates_before': [5629.00, 454.33, 30.60, 3.36, 1.25, 0.98],
            'candidates_after': [453.32, 29.86, 2.84, 0.88, 0.60, 0.35],
            'reduction_pct': [91.95, 93.39, 90.48, 68.21, 49.51, 36.75],
            'info_gain': [5.16, 4.29, 2.33, 0.76, 0.29, 0.28],
            'n_games': 5330
        },
        'Zero-shot': {
            'candidates_before': [5629.00, 439.86, 29.59, 3.66, 1.39, 0.92],
            'candidates_after': [439.86, 28.84, 3.09, 1.02, 0.64, 0.50],
            'reduction_pct': [92.19, 93.56, 88.68, 71.25, 53.78, 44.28],
            'info_gain': [5.18, 4.42, 2.11, 0.78, 0.37, 0.21],
            'n_games': 5199
        }
    }

    rounds = list(range(1, 7))

    # Create figure with subplots
    fig = plt.figure(figsize=(20, 12))
    gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

    # 1. Hamming Distance Convergence
    ax1 = fig.add_subplot(gs[0, 0])
    for category, values in data.items():
        ax1.plot(rounds, values['hamming'], marker='o', linewidth=2.5,
                markersize=8, label=f"{category} (n={values['n_games']:,})")
    ax1.set_xlabel('Round', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Hamming Distance', fontsize=12, fontweight='bold')
    ax1.set_title('A. Convergence: Hamming Distance by Round', fontsize=14, fontweight='bold')
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3)
    ax1.set_xticks(rounds)

    # 2. Levenshtein Distance Convergence
    ax2 = fig.add_subplot(gs[0, 1])
    for category, values in data.items():
        ax2.plot(rounds, values['levenshtein'], marker='s', linewidth=2.5,
                markersize=8, label=f"{category}")
    ax2.set_xlabel('Round', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Levenshtein Distance', fontsize=12, fontweight='bold')
    ax2.set_title('B. Convergence: Levenshtein Distance by Round', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(rounds)

    # 3. Convergence Rate Comparison (bar chart)
    ax3 = fig.add_subplot(gs[0, 2])
    categories = list(data.keys())
    convergence_rates = [
        0.3017,  # Pure Algorithms
        0.8159,  # Hybrids (Zero-shot)
        0.8462   # Hybrids (CoT)
    ]
    colors = sns.color_palette("husl", 3)
    bars = ax3.bar(range(len(categories)), convergence_rates, color=colors, alpha=0.8, edgecolor='black')
    ax3.set_ylabel('Hamming Decrease per Round', fontsize=12, fontweight='bold')
    ax3.set_title('C. Convergence Rate Comparison', fontsize=14, fontweight='bold')
    ax3.set_xticks(range(len(categories)))
    ax3.set_xticklabels(categories, rotation=15, ha='right', fontsize=10)
    ax3.grid(True, alpha=0.3, axis='y')

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, convergence_rates)):
        height = bar.get_height()
        ax3.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.4f}', ha='center', va='bottom', fontweight='bold', fontsize=10)

    # 4. Search Space Reduction (LLMs) - log scale
    ax4 = fig.add_subplot(gs[1, 0])
    for strategy, values in llm_data.items():
        ax4.plot(rounds, values['candidates_before'], marker='o', linewidth=2.5,
                markersize=8, label=f"{strategy} - Before", linestyle='-')
        ax4.plot(rounds, values['candidates_after'], marker='s', linewidth=2.5,
                markersize=8, label=f"{strategy} - After", linestyle='--')
    ax4.set_yscale('log')
    ax4.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Candidate Count (log scale)', fontsize=12, fontweight='bold')
    ax4.set_title('D. Search Space Reduction (Pure LLMs)', fontsize=14, fontweight='bold')
    ax4.legend(fontsize=9)
    ax4.grid(True, alpha=0.3, which='both')
    ax4.set_xticks(rounds)

    # 5. Pruning Efficiency (%)
    ax5 = fig.add_subplot(gs[1, 1])
    for strategy, values in llm_data.items():
        ax5.plot(rounds, values['reduction_pct'], marker='o', linewidth=2.5,
                markersize=8, label=f"{strategy} (n={values['n_games']:,})")
    ax5.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax5.set_ylabel('Search Space Reduction (%)', fontsize=12, fontweight='bold')
    ax5.set_title('E. Pruning Efficiency by Attempt', fontsize=14, fontweight='bold')
    ax5.legend(fontsize=10)
    ax5.grid(True, alpha=0.3)
    ax5.set_xticks(rounds)
    ax5.axhline(y=50, color='red', linestyle=':', alpha=0.5, label='50% threshold')

    # 6. Information Gain
    ax6 = fig.add_subplot(gs[1, 2])
    for strategy, values in llm_data.items():
        ax6.plot(rounds, values['info_gain'], marker='o', linewidth=2.5,
                markersize=8, label=strategy)
    ax6.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax6.set_ylabel('Information Gain (bits)', fontsize=12, fontweight='bold')
    ax6.set_title('F. Information Gain per Attempt', fontsize=14, fontweight='bold')
    ax6.legend(fontsize=10)
    ax6.grid(True, alpha=0.3)
    ax6.set_xticks(rounds)

    # 7. Cumulative Information Gain
    ax7 = fig.add_subplot(gs[2, 0])
    for strategy, values in llm_data.items():
        cumulative = np.cumsum(values['info_gain'])
        ax7.plot(rounds, cumulative, marker='o', linewidth=2.5,
                markersize=8, label=strategy)
    ax7.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax7.set_ylabel('Cumulative Information Gain (bits)', fontsize=12, fontweight='bold')
    ax7.set_title('G. Cumulative Information Gain', fontsize=14, fontweight='bold')
    ax7.legend(fontsize=10)
    ax7.grid(True, alpha=0.3)
    ax7.set_xticks(rounds)
    # Add theoretical maximum line
    ax7.axhline(y=np.log2(5629), color='red', linestyle=':', alpha=0.5,
                label=f'Theoretical max: {np.log2(5629):.2f} bits')

    # 8. Convergence Efficiency Comparison
    ax8 = fig.add_subplot(gs[2, 1])
    categories_all = ['Pure\nAlgorithms', 'Hybrids\n(Zero-shot)', 'Hybrids\n(CoT)']
    total_decrease = [33.32, 90.04, 91.55]
    colors = sns.color_palette("husl", 3)
    bars = ax8.bar(range(len(categories_all)), total_decrease, color=colors, alpha=0.8, edgecolor='black')
    ax8.set_ylabel('Total Distance Decrease (%)', fontsize=12, fontweight='bold')
    ax8.set_title('H. Total Convergence Efficiency', fontsize=14, fontweight='bold')
    ax8.set_xticks(range(len(categories_all)))
    ax8.set_xticklabels(categories_all, fontsize=11)
    ax8.grid(True, alpha=0.3, axis='y')
    ax8.set_ylim([0, 100])

    # Add value labels
    for bar, val in zip(bars, total_decrease):
        height = bar.get_height()
        ax8.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # 9. Performance Relative to Algorithm Baseline
    ax9 = fig.add_subplot(gs[2, 2])
    relative_performance = [100, 270.4, 280.5]  # Relative to algorithm baseline
    colors = sns.color_palette("husl", 3)
    bars = ax9.bar(range(len(categories_all)), relative_performance, color=colors, alpha=0.8, edgecolor='black')
    ax9.set_ylabel('Performance vs Algorithm Baseline (%)', fontsize=12, fontweight='bold')
    ax9.set_title('I. Relative Performance (Algorithm = 100%)', fontsize=14, fontweight='bold')
    ax9.set_xticks(range(len(categories_all)))
    ax9.set_xticklabels(categories_all, fontsize=11)
    ax9.grid(True, alpha=0.3, axis='y')
    ax9.axhline(y=100, color='red', linestyle='--', alpha=0.5, linewidth=2, label='Algorithm baseline')
    ax9.legend(fontsize=10)

    # Add value labels
    for bar, val in zip(bars, relative_performance):
        height = bar.get_height()
        ax9.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=11)

    # Overall title
    fig.suptitle('Convergence Patterns and Search Space Pruning Analysis:\nIterative Reasoning Ability in LLMs vs Algorithms',
                fontsize=16, fontweight='bold', y=0.995)

    # Save figure
    output_path = '/Users/kevin/Desktop/wordle/convergence_trajectories.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"Convergence trajectories plot saved to: {output_path}")

    # Also save as PDF
    output_path_pdf = '/Users/kevin/Desktop/wordle/convergence_trajectories.pdf'
    plt.savefig(output_path_pdf, bbox_inches='tight', facecolor='white')
    print(f"PDF version saved to: {output_path_pdf}")

    plt.close()

    # Create a second figure focusing on LLM reasoning patterns
    fig2, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig2.suptitle('LLM Iterative Reasoning Patterns: Evidence of Systematic Belief Updating',
                  fontsize=16, fontweight='bold')

    # 1. Search space reduction trajectory
    ax = axes[0, 0]
    for strategy, values in llm_data.items():
        reduction = [(before - after) for before, after in
                    zip(values['candidates_before'], values['candidates_after'])]
        ax.plot(rounds, reduction, marker='o', linewidth=2.5, markersize=8, label=strategy)
    ax.set_yscale('log')
    ax.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax.set_ylabel('Candidates Eliminated (log scale)', fontsize=12, fontweight='bold')
    ax.set_title('A. Candidates Eliminated per Attempt', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, which='both')
    ax.set_xticks(rounds)

    # 2. Average pruning efficiency by attempt
    ax = axes[0, 1]
    attempts = list(range(1, 7))
    cot_eff = llm_data['Chain-of-Thought']['reduction_pct']
    zs_eff = llm_data['Zero-shot']['reduction_pct']

    x = np.arange(len(attempts))
    width = 0.35

    ax.bar(x - width/2, cot_eff, width, label='Chain-of-Thought', alpha=0.8, edgecolor='black')
    ax.bar(x + width/2, zs_eff, width, label='Zero-shot', alpha=0.8, edgecolor='black')
    ax.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax.set_ylabel('Pruning Efficiency (%)', fontsize=12, fontweight='bold')
    ax.set_title('B. Pruning Efficiency Comparison', fontsize=13, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(attempts)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='70% threshold')

    # 3. Information gain rate
    ax = axes[1, 0]
    for strategy, values in llm_data.items():
        ax.bar(np.arange(len(rounds)) + (0.2 if strategy == 'Zero-shot' else -0.2),
              values['info_gain'], width=0.35, label=strategy, alpha=0.8, edgecolor='black')
    ax.set_xlabel('Attempt', fontsize=12, fontweight='bold')
    ax.set_ylabel('Information Gain (bits)', fontsize=12, fontweight='bold')
    ax.set_title('C. Information Gain Distribution', fontsize=13, fontweight='bold')
    ax.set_xticks(range(len(rounds)))
    ax.set_xticklabels(rounds)
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3, axis='y')

    # 4. Efficiency decline rate
    ax = axes[1, 1]
    for strategy, values in llm_data.items():
        # Calculate rate of decline in pruning efficiency
        efficiency = values['reduction_pct']
        decline_rate = [efficiency[i] - efficiency[i+1] for i in range(len(efficiency)-1)]
        ax.plot(rounds[:-1], decline_rate, marker='o', linewidth=2.5, markersize=8, label=strategy)
    ax.set_xlabel('Attempt Transition', fontsize=12, fontweight='bold')
    ax.set_ylabel('Efficiency Decline (percentage points)', fontsize=12, fontweight='bold')
    ax.set_title('D. Pruning Efficiency Decline Rate', fontsize=13, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    ax.axhline(y=0, color='black', linestyle='-', alpha=0.3)

    plt.tight_layout()

    output_path2 = '/Users/kevin/Desktop/wordle/llm_reasoning_patterns.png'
    plt.savefig(output_path2, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"LLM reasoning patterns plot saved to: {output_path2}")

    output_path2_pdf = '/Users/kevin/Desktop/wordle/llm_reasoning_patterns.pdf'
    plt.savefig(output_path2_pdf, bbox_inches='tight', facecolor='white')
    print(f"PDF version saved to: {output_path2_pdf}")

    plt.close()

    print("\nAll visualizations created successfully!")

if __name__ == "__main__":
    create_convergence_plots()
