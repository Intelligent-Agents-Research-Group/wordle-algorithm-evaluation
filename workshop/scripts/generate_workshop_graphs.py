#!/usr/bin/env python3
"""
Generate graphs for the workshop paper on hybrid LLM-algorithm agents.

Creates visualizations comparing:
- Pure Algorithms (CSS, VOI)
- Hybrid strategies (LLM-First, Algo-First)

Metrics shown:
1. Win Rate
2. Average Attempts
3. Hamming Distance (convergence trajectory)
4. Convergence Rate
5. Space Reduction (first round)
6. Constraint Violations
"""

import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from collections import defaultdict

# Setup paths
SCRIPT_DIR = Path(__file__).parent
WORKSHOP_DIR = SCRIPT_DIR.parent
PROJECT_DIR = WORKSHOP_DIR.parent
RESULTS_DIR = WORKSHOP_DIR / "results_css"
RESULTS_OLD_DIR = WORKSHOP_DIR / "results_old_css"
OUTPUT_DIR = WORKSHOP_DIR / "plots"
OUTPUT_DIR.mkdir(exist_ok=True)

# Pure data paths
ALGO_DATA = PROJECT_DIR / "results/algorithms"

# Color scheme
COLORS = {
    'css': '#1f77b4',            # Blue
    'voi': '#2ca02c',            # Green
    'llm_first': '#17becf',      # Cyan
    'algo_first': '#d62728',     # Red
    'alternating': '#ff7f0e',    # Orange
}

LABELS = {
    'css': 'CSS',
    'voi': 'VOI',
    'llm_first': 'Hybrid\nLLM-First',
    'algo_first': 'Hybrid\nAlgo-First',
    'alternating': 'Hybrid\nAlternating',
}


def load_pure_algorithm_data():
    """Load pure algorithm results (CSS, VOI)."""
    results = {}

    # CSS
    css_file = ALGO_DATA / "css/css_results_with_candidates.csv"
    if css_file.exists():
        df = pd.read_csv(css_file)
        avg_attempts = df[df['won'] == True]['attempts'].mean()
        hamming = [df[f'hamming_{r}'].mean() for r in range(1, 7)]
        # Convergence rate: (hamming_1 - hamming_final) / avg_attempts
        # hamming_final = 0 for won games
        convergence = (hamming[0] - 0) / avg_attempts if avg_attempts > 0 else 0

        results['css'] = {
            'win_rate': df['won'].mean() * 100,
            'attempts': avg_attempts,
            'reduction_rate_1': df['reduction_rate_1'].mean() if 'reduction_rate_1' in df.columns else None,
            'n_games': len(df),
            'violations': 0.0,  # Algorithms have 0 violations by design
            'hamming': hamming,
            'convergence_rate': convergence,
        }

    # VOI
    algo_file = ALGO_DATA / "raw data/algorithm_results_with_candidates.csv"
    if algo_file.exists():
        df = pd.read_csv(algo_file)
        sdf = df[df['strategy'] == 'voi']
        if len(sdf) > 0:
            avg_attempts = sdf[sdf['won'] == True]['attempts'].mean()
            hamming = [sdf[f'hamming_{r}'].mean() for r in range(1, 7)]
            convergence = (hamming[0] - 0) / avg_attempts if avg_attempts > 0 else 0

            results['voi'] = {
                'win_rate': sdf['won'].mean() * 100,
                'attempts': avg_attempts,
                'reduction_rate_1': sdf['reduction_rate_1'].mean() if 'reduction_rate_1' in sdf.columns else None,
                'n_games': len(sdf),
                'violations': 0.0,
                'hamming': hamming,
                'convergence_rate': convergence,
            }

    return results


def load_workshop_data():
    """Load workshop hybrid data from both new and old results."""
    summaries = []
    csvs = {}

    # Load from new CSS results
    for summary_file in RESULTS_DIR.rglob("summary_*.json"):
        with open(summary_file) as f:
            data = json.load(f)
            data['file_path'] = str(summary_file)
            summaries.append(data)

    for csv_file in RESULTS_DIR.rglob("*.csv"):
        if not csv_file.name.startswith("summary"):
            csvs[csv_file.stem] = pd.read_csv(csv_file)

    # Also load alternating data from old CSS results (group_c)
    old_group_c = RESULTS_OLD_DIR / "group_c"
    if old_group_c.exists():
        for csv_file in old_group_c.rglob("*.csv"):
            if not csv_file.name.startswith("summary"):
                # Prefix with 'old_' to avoid conflicts
                csvs[f"old_{csv_file.stem}"] = pd.read_csv(csv_file)

    return summaries, csvs


def categorize_config(config_name):
    """Categorize config as LLM-first, Algorithm-first, or Alternating."""
    config = config_name.lower()

    # LLM-first patterns (check first - L_to_C_alt is LLM-first, not alternating)
    if config.startswith('l_to') or config.startswith('l1_to') or \
       config.startswith('l2_to') or config.startswith('l3_to') or \
       'llm_first' in config:
        return 'llm_first'

    # True alternating patterns: alt_css_start, alt_voi_start, alternating_algorithm_first
    # These alternate every round between LLM and algorithm
    if config.startswith('alt_css') or config.startswith('alt_voi') or \
       config.startswith('alternating_algorithm') or config.startswith('old_alternating'):
        return 'alternating'

    # Algo-first patterns
    if config.startswith('c_to') or config.startswith('v_to') or \
       ('css' in config and '_to_l' in config) or \
       ('voi' in config and '_to_l' in config) or \
       (config.startswith('rerank_css') and 'llm_first' not in config) or \
       (config.startswith('rerank_voi') and 'llm_first' not in config) or \
       config.startswith('constraint_filter'):
        return 'algo_first'

    return None


def aggregate_hybrid_data(workshop_summaries, workshop_csvs):
    """Aggregate hybrid data by category."""
    hybrid_data = {
        'llm_first': {
            'win_rate': [], 'attempts': [], 'violations': [],
            'reduction_rate_1': [], 'hamming': [[] for _ in range(6)]
        },
        'algo_first': {
            'win_rate': [], 'attempts': [], 'violations': [],
            'reduction_rate_1': [], 'hamming': [[] for _ in range(6)]
        },
        'alternating': {
            'win_rate': [], 'attempts': [], 'violations': [],
            'reduction_rate_1': [], 'hamming': [[] for _ in range(6)]
        }
    }

    # Track which configs have summaries (to avoid double counting)
    configs_with_summaries = set()

    # Get data from summaries (new CSS results have these)
    for s in workshop_summaries:
        config = s.get('config_name', 'unknown')
        category = categorize_config(config)
        if category:
            hybrid_data[category]['win_rate'].append(s.get('win_rate', 0) * 100)
            hybrid_data[category]['attempts'].append(s.get('avg_attempts_when_won', 0))
            configs_with_summaries.add(config.lower())

    # Get violations, hamming, and basic stats from CSVs
    for name, df in workshop_csvs.items():
        category = categorize_config(name)
        if not category:
            continue

        if 'total_violations' in df.columns:
            hybrid_data[category]['violations'].append(df['total_violations'].mean())

        if 'reduction_rate_1' in df.columns:
            hybrid_data[category]['reduction_rate_1'].append(df['reduction_rate_1'].mean())

        # Only extract win_rate/attempts from CSVs that don't have summaries
        # (e.g., old alternating data prefixed with 'old_')
        is_old_data = name.startswith('old_')
        if is_old_data and 'won' in df.columns:
            hybrid_data[category]['win_rate'].append(df['won'].mean() * 100)
            won_games = df[df['won'] == True]
            if len(won_games) > 0:
                hybrid_data[category]['attempts'].append(won_games['attempts'].mean())

        for r in range(6):
            col = f'hamming_{r+1}'
            if col in df.columns:
                hybrid_data[category]['hamming'][r].extend(df[col].dropna().tolist())

    # Calculate aggregated metrics
    results = {}
    for category in ['llm_first', 'algo_first', 'alternating']:
        d = hybrid_data[category]
        if d['win_rate'] or d['hamming'][0]:  # Have either summary or CSV data
            avg_attempts = np.mean(d['attempts']) if d['attempts'] else 4.0
            hamming_1 = np.mean(d['hamming'][0]) if d['hamming'][0] else 4.0

            # Get the last non-nan hamming value for final distance
            hamming_vals = [np.mean(d['hamming'][r]) if d['hamming'][r] else np.nan for r in range(6)]
            hamming_final = 0  # When won, final distance is 0

            # Convergence rate = (initial - final) / num_rounds
            # Using avg_attempts as proxy for num_rounds
            convergence = (hamming_1 - hamming_final) / avg_attempts if avg_attempts > 0 else 0

            results[category] = {
                'win_rate': np.mean(d['win_rate']) if d['win_rate'] else 0,
                'win_rate_std': np.std(d['win_rate']) if d['win_rate'] else 0,
                'attempts': avg_attempts,
                'attempts_std': np.std(d['attempts']) if d['attempts'] else 0,
                'violations': np.mean(d['violations']) if d['violations'] else 0,
                'violations_std': np.std(d['violations']) if d['violations'] else 0,
                'reduction_rate_1': np.mean(d['reduction_rate_1']) if d['reduction_rate_1'] else 0,
                'hamming': hamming_vals,
                'convergence_rate': convergence,
                'n_configs': len(d['win_rate']) if d['win_rate'] else len(d['violations'])
            }

    return results


def create_six_metric_figure(algo_data, hybrid_data):
    """Create a 2x3 figure with all 6 metrics."""
    fig, axes = plt.subplots(2, 3, figsize=(16, 10))

    categories = ['css', 'voi', 'llm_first', 'algo_first', 'alternating']
    colors = [COLORS[c] for c in categories]
    labels = [LABELS[c] for c in categories]

    # Gather all data
    data = {}
    for cat in categories:
        if cat in algo_data:
            data[cat] = algo_data[cat]
        elif cat in hybrid_data:
            data[cat] = hybrid_data[cat]

    x = np.arange(len(categories))

    # 1. Win Rate (top left)
    ax = axes[0, 0]
    values = [data[c]['win_rate'] for c in categories]
    stds = [data[c].get('win_rate_std', 0) for c in categories]
    bars = ax.bar(x, values, yerr=stds, capsize=4, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Win Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('Win Rate', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 110)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # 2. Average Attempts (top middle)
    ax = axes[0, 1]
    values = [data[c]['attempts'] for c in categories]
    stds = [data[c].get('attempts_std', 0) for c in categories]
    bars = ax.bar(x, values, yerr=stds, capsize=4, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Avg Attempts', fontsize=11, fontweight='bold')
    ax.set_title('Average Attempts (when won)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # 3. Convergence Rate (top right)
    ax = axes[0, 2]
    values = [data[c]['convergence_rate'] for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Convergence Rate', fontsize=11, fontweight='bold')
    ax.set_title('Convergence Rate\n(Hamming₁ / Attempts)', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 1.5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # 4. Space Reduction (bottom left)
    ax = axes[1, 0]
    values = [data[c].get('reduction_rate_1', 0) or 0 for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Reduction Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('First-Round Space Reduction', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, 100)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # 5. Hamming Distance Trajectory (bottom middle)
    ax = axes[1, 1]
    rounds = [1, 2, 3, 4, 5, 6]
    for cat in categories:
        if 'hamming' in data[cat]:
            hamming = data[cat]['hamming']
            ax.plot(rounds, hamming, marker='o', linewidth=2, markersize=6,
                   color=COLORS[cat], label=LABELS[cat].replace('\n', ' '))
    ax.set_xlabel('Round', fontsize=11, fontweight='bold')
    ax.set_ylabel('Average Hamming Distance to Target', fontsize=11, fontweight='bold')
    ax.set_title('Hamming Distance by Round', fontsize=12, fontweight='bold')
    ax.set_xticks(rounds)
    ax.set_ylim(0, 5)
    ax.legend(loc='upper right', fontsize=8)
    ax.grid(True, alpha=0.3)

    # 6. Violations (bottom right)
    ax = axes[1, 2]
    values = [data[c].get('violations', 0) for c in categories]
    stds = [data[c].get('violations_std', 0) for c in categories]
    bars = ax.bar(x, values, yerr=stds, capsize=4, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
    ax.set_ylabel('Violations per Game', fontsize=11, fontweight='bold')
    ax.set_title('Constraint Violations', fontsize=12, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylim(0, max(values) * 1.5 if max(values) > 0 else 0.5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)

    # Add group labels (skip for hamming trajectory plot)
    for i, ax in enumerate(axes.flat):
        if i != 4:  # Skip the hamming trajectory plot (index 4)
            ax.text(0.15, -0.22, 'Pure Algo', transform=ax.transAxes,
                    ha='center', fontsize=9, style='italic', color='#666')
            ax.text(0.7, -0.22, 'Hybrid', transform=ax.transAxes,
                    ha='center', fontsize=9, style='italic', color='#666')

    plt.tight_layout()
    plt.subplots_adjust(bottom=0.1, hspace=0.35)

    plt.savefig(OUTPUT_DIR / 'workshop_all_metrics.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'workshop_all_metrics.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'workshop_all_metrics.png'}")
    plt.close()


def create_individual_plots(algo_data, hybrid_data):
    """Create individual plots for each metric."""
    categories = ['css', 'voi', 'llm_first', 'algo_first', 'alternating']
    colors = [COLORS[c] for c in categories]
    labels = [LABELS[c] for c in categories]

    data = {}
    for cat in categories:
        if cat in algo_data:
            data[cat] = algo_data[cat]
        elif cat in hybrid_data:
            data[cat] = hybrid_data[cat]

    x = np.arange(len(categories))

    # Win Rate plot
    fig, ax = plt.subplots(figsize=(8, 6))
    values = [data[c]['win_rate'] for c in categories]
    stds = [data[c].get('win_rate_std', 0) for c in categories]
    bars = ax.bar(x, values, yerr=stds, capsize=4, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_ylabel('Win Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Win Rate Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 110)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'win_rate.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'win_rate.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'win_rate.png'}")
    plt.close()

    # Average Attempts plot
    fig, ax = plt.subplots(figsize=(8, 6))
    values = [data[c]['attempts'] for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.05,
                f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_ylabel('Average Attempts', fontsize=12, fontweight='bold')
    ax.set_title('Average Attempts Comparison', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig3_attempts.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig3_attempts.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'fig3_attempts.png'}")
    plt.close()

    # Reduction Rate plot
    fig, ax = plt.subplots(figsize=(8, 6))
    values = [data[c].get('reduction_rate_1', 0) or 0 for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{val:.1f}%', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_ylabel('First-Round Reduction Rate (%)', fontsize=12, fontweight='bold')
    ax.set_title('Search Space Reduction', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 105)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig4_reduction_rate.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig4_reduction_rate.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'fig4_reduction_rate.png'}")
    plt.close()

    # Convergence Rate plot
    fig, ax = plt.subplots(figsize=(8, 6))
    values = [data[c]['convergence_rate'] for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_ylabel('Convergence Rate', fontsize=12, fontweight='bold')
    ax.set_title('Convergence Rate (Hamming₁ / Attempts)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 1.5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig7_convergence_rate.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig7_convergence_rate.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'fig7_convergence_rate.png'}")
    plt.close()

    # Violations plot
    fig, ax = plt.subplots(figsize=(8, 6))
    values = [data[c].get('violations', 0) for c in categories]
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.02,
                f'{val:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
    ax.set_ylabel('Violations per Game', fontsize=12, fontweight='bold')
    ax.set_title('Constraint Violations', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, max(values) * 1.3 if max(values) > 0 else 0.5)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.axvline(x=1.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig6_violations.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig6_violations.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'fig6_violations.png'}")
    plt.close()

    # Convergence trajectory plot
    fig, ax = plt.subplots(figsize=(10, 6))
    rounds = [1, 2, 3, 4, 5, 6]
    for cat in categories:
        if 'hamming' in data[cat]:
            hamming = data[cat]['hamming']
            ax.plot(rounds, hamming, marker='o', linewidth=2.5, markersize=8,
                   color=COLORS[cat], label=LABELS[cat].replace('\n', ' '))
    ax.set_xlabel('Round', fontsize=12, fontweight='bold')
    ax.set_ylabel('Average Hamming Distance to Target', fontsize=12, fontweight='bold')
    ax.set_title('Hamming Distance by Round', fontsize=14, fontweight='bold')
    ax.set_xticks(rounds)
    ax.set_ylim(0, 5)
    ax.legend(loc='upper right', fontsize=10)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig5_hamming_distance.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig5_hamming_distance.pdf', bbox_inches='tight')
    print(f"Saved: {OUTPUT_DIR / 'fig5_hamming_distance.png'}")
    plt.close()


def print_summary_table(algo_data, hybrid_data):
    """Print summary statistics table."""
    print("\n" + "="*90)
    print("WORKSHOP SUMMARY STATISTICS (Pure Algorithms vs Hybrids)")
    print("="*90)
    print(f"{'Category':<20} {'N':>6} {'Win%':>8} {'Attempts':>10} {'Convg':>8} {'SpaceRed':>10} {'Viols':>8}")
    print("-"*90)

    categories = ['css', 'voi', 'llm_first', 'algo_first', 'alternating']
    labels = {'css': 'CSS', 'voi': 'VOI', 'llm_first': 'Hybrid LLM-First', 'algo_first': 'Hybrid Algo-First', 'alternating': 'Hybrid Alternating'}

    for cat in categories:
        if cat in algo_data:
            d = algo_data[cat]
            n = d.get('n_games', '-')
        elif cat in hybrid_data:
            d = hybrid_data[cat]
            n = d.get('n_configs', '-')
        else:
            continue

        wr = f"{d['win_rate']:.1f}%"
        att = f"{d['attempts']:.2f}"
        conv = f"{d['convergence_rate']:.2f}"
        sr = f"{d.get('reduction_rate_1', 0):.1f}%" if d.get('reduction_rate_1') else "N/A"
        viol = f"{d.get('violations', 0):.2f}"

        print(f"{labels[cat]:<20} {n:>6} {wr:>8} {att:>10} {conv:>8} {sr:>10} {viol:>8}")

        if cat == 'voi':
            print("-"*90)

    print("="*90)


def main():
    print("Loading data...")

    # Load all data sources
    algo_data = load_pure_algorithm_data()
    print(f"  Loaded {len(algo_data)} pure algorithm results")

    workshop_summaries, workshop_csvs = load_workshop_data()
    print(f"  Loaded {len(workshop_summaries)} workshop summaries, {len(workshop_csvs)} CSVs")

    hybrid_data = aggregate_hybrid_data(workshop_summaries, workshop_csvs)
    print(f"  Aggregated {len(hybrid_data)} hybrid categories")

    print("\nGenerating graphs...")

    # Create all graphs
    create_six_metric_figure(algo_data, hybrid_data)
    create_individual_plots(algo_data, hybrid_data)

    # Print summary
    print_summary_table(algo_data, hybrid_data)

    print(f"\nAll graphs saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
