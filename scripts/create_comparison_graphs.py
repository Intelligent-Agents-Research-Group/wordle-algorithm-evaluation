#!/usr/bin/env python3
"""
Create comparison graphs for Wordle strategy win rates.
Compares: CSS, VOI, Pure Random, Random, LLMs (by category), and Hybrids.

Updated January 22, 2026 to use True CSS (minimax regret) results.
"""

import json
import math
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from pathlib import Path

# Set up paths
PROJECT_DIR = Path(__file__).parent.parent
RESULTS_DIR = PROJECT_DIR / "results"

# ============================================================================
# SHARED CONSTANTS
# ============================================================================

# LLM tier definitions — must match full_anova_analysis.py
LLM_TIERS = {
    'Small_LLM': ['mistral_7b_instruct', 'llama_3.1_8b_instruct', 'granite_3.3_8b_instruct',
                   'llama_3.1_nemotron_nano_8B', 'mistral_small_3.1'],
    'Mid_LLM': ['gemma_3_27b_it', 'codestral_22b', 'gpt_oss_20b'],
    'Frontier_LLM': ['llama_3.3_70b_instruct', 'llama_3.1_70b_instruct', 'gpt_oss_120b'],
}

APPROACHES = ['Pure Random', 'Random', 'VOI', 'CSS',
              'Small_LLM', 'Mid_LLM', 'Frontier_LLM', 'Hybrid']

# ============================================================================
# RAW DATA LOADING — reads directly from experimental result files
# ============================================================================

_RAW_DATA_CACHE = None


def _load_single_llm(filepath):
    """Load a single LLM CSV (attempt-level) and aggregate to game-level."""
    df = pd.read_csv(filepath)

    def hamming(s1, s2):
        if pd.isna(s1) or pd.isna(s2):
            return np.nan
        s1, s2 = str(s1).upper(), str(s2).upper()
        return sum(c1 != c2 for c1, c2 in zip(s1, s2))

    df['hamming'] = df.apply(lambda r: hamming(r['guess'], r['target_word']), axis=1)

    game_data = df.groupby('game_id').agg({
        'target_word': 'first',
        'win': 'max',
        'attempts_to_win': 'max',
        'total_constraint_violations': 'sum'
    }).reset_index()

    first_attempt = df[df['attempt_number'] == 1].set_index('game_id')
    if 'candidates_after' in first_attempt.columns:
        game_data['candidates_after_1'] = game_data['game_id'].map(first_attempt['candidates_after'])
    if 'candidate_reduction_rate' in first_attempt.columns:
        game_data['reduction_rate_1'] = game_data['game_id'].map(first_attempt['candidate_reduction_rate'])

    for r in range(1, 7):
        attempt_r = df[df['attempt_number'] == r].set_index('game_id')
        if len(attempt_r) > 0:
            game_data[f'hamming_{r}'] = game_data['game_id'].map(attempt_r['hamming'])

    game_data = game_data.rename(columns={
        'win': 'won',
        'attempts_to_win': 'attempts',
        'total_constraint_violations': 'total_violations'
    })
    return game_data


def _average_dfs_by_target(dfs, numeric_cols):
    """Average multiple DataFrames by target_word, keeping only shared target words."""
    if len(dfs) == 1:
        return dfs[0]
    merged = dfs[0][['target_word']].copy()
    for col in numeric_cols:
        col_values = []
        for md in dfs:
            if col in md.columns:
                col_values.append(md.set_index('target_word')[col])
        if col_values:
            combined = pd.concat(col_values, axis=1)
            merged[col] = combined.mean(axis=1).reindex(merged['target_word']).values
    return merged


def _load_all_raw_data():
    """Load all raw experimental data and return dict of game-level DataFrames.

    Returns dict keyed by approach name, each value a DataFrame with columns:
      target_word, won, attempts, total_violations, candidates_after_1,
      reduction_rate_1, hamming_1 through hamming_6
    """
    global _RAW_DATA_CACHE
    if _RAW_DATA_CACHE is not None:
        return _RAW_DATA_CACHE

    result = {}
    numeric_cols = ['won', 'attempts', 'total_violations', 'candidates_after_1',
                    'reduction_rate_1', 'hamming_1', 'hamming_2', 'hamming_3',
                    'hamming_4', 'hamming_5', 'hamming_6']

    # ---- 1. Algorithm data (pure_random, random, voi) ----
    algo_base = PROJECT_DIR / "results/algorithms/raw data/algorithm_results_20251211_175156.csv"
    algo_viol = PROJECT_DIR / "results/algorithms/raw data/algorithm_results_with_violations.csv"
    algo_cand = PROJECT_DIR / "results/algorithms/raw data/algorithm_results_with_candidates.csv"

    df_base = pd.read_csv(algo_base)
    df_viol = pd.read_csv(algo_viol) if algo_viol.exists() else None
    df_cand = pd.read_csv(algo_cand) if algo_cand.exists() else None

    for strategy, label in [('pure_random', 'Pure Random'), ('random', 'Random'), ('voi', 'VOI')]:
        sdf = df_base[df_base['strategy'] == strategy].copy()

        if df_viol is not None:
            sv = df_viol[df_viol['strategy'] == strategy]
            for col in sv.columns:
                if ('violated' in col or 'total_violations' in col) and col not in sdf.columns:
                    sdf[col] = sv[col].values

        # Sum per-round violations into total_violations if not already present
        if 'total_violations' not in sdf.columns:
            vc = [c for c in sdf.columns if c.startswith('total_violations_')]
            if vc:
                sdf['total_violations'] = sdf[vc].sum(axis=1)

        if df_cand is not None:
            sc = df_cand[df_cand['strategy'] == strategy]
            for col in sc.columns:
                if ('candidates' in col or 'reduction' in col) and col not in sdf.columns:
                    sdf[col] = sc[col].values

        result[label] = sdf

    # ---- 2. True CSS ----
    css_viol = PROJECT_DIR / "results/algorithms/true_css/css_true_results_with_violations.csv"
    css_cand = PROJECT_DIR / "results/algorithms/true_css/css_true_results_with_candidates.csv"

    css_df = pd.read_csv(css_viol)
    if 'total_violations' not in css_df.columns:
        vc = [c for c in css_df.columns if c.startswith('total_violations_')]
        if vc:
            css_df['total_violations'] = css_df[vc].sum(axis=1)
    if css_cand.exists():
        cc = pd.read_csv(css_cand)
        for col in cc.columns:
            if ('candidates' in col or 'reduction' in col) and col not in css_df.columns:
                css_df[col] = cc[col]
    result['CSS'] = css_df

    # ---- 3. LLM tiers ----
    llm_dir = PROJECT_DIR / "results/llms/raw data"
    for tier_name, model_patterns in LLM_TIERS.items():
        model_dfs = []
        for pattern in model_patterns:
            files = list(llm_dir.glob(f"*{pattern}*.csv"))
            zero_shot = [f for f in files if 'zero-shot' in f.name]
            if not zero_shot:
                continue
            model_dfs.append(_load_single_llm(zero_shot[0]))

        if model_dfs:
            result[tier_name] = _average_dfs_by_target(model_dfs, numeric_cols)

    # ---- 4. Hybrid ----
    hybrid_dir = PROJECT_DIR / "results/hybrids/stage3/raw data"
    if hybrid_dir.exists():
        hybrid_dfs = []
        for f in sorted(hybrid_dir.glob('alternating_llm_first_*.csv')):
            if '_with_' in f.name:
                continue
            hdf = pd.read_csv(f)

            # Sum per-round violations into total_violations
            viol_cols = [c for c in hdf.columns if c.startswith('total_violations_')]
            if viol_cols:
                hdf['total_violations'] = hdf[viol_cols].sum(axis=1)
            else:
                # Try loading from _with_violations file
                viol_file = f.parent / (f.stem + '_with_violations.csv')
                if viol_file.exists():
                    vdf = pd.read_csv(viol_file)
                    vc = [c for c in vdf.columns if c.startswith('total_violations_')]
                    if vc:
                        hdf['total_violations'] = vdf[vc].sum(axis=1)
                    else:
                        hdf['total_violations'] = 0
                else:
                    hdf['total_violations'] = 0

            # Merge candidates data
            cand_file = f.parent / (f.stem + '_with_candidates.csv')
            if cand_file.exists():
                cdf = pd.read_csv(cand_file)
                for col in ['candidates_after_1', 'reduction_rate_1']:
                    if col in cdf.columns and col not in hdf.columns:
                        hdf[col] = cdf[col].values

            hybrid_dfs.append(hdf)

        if hybrid_dfs:
            result['Hybrid'] = _average_dfs_by_target(hybrid_dfs, numeric_cols)

    _RAW_DATA_CACHE = result
    return result


# ============================================================================
# METRIC LOADING — each computes one metric from raw data
# ============================================================================

def load_actual_win_rates():
    """Compute win rates directly from raw experimental data."""
    data = _load_all_raw_data()
    rates = {}
    for approach in APPROACHES:
        if approach not in data:
            rates[approach] = 0
            continue
        df = data[approach]
        won_col = 'won' if 'won' in df.columns else 'win'
        rates[approach] = df[won_col].mean() * 100
    return rates


ACTUAL_WIN_RATES = load_actual_win_rates()


def load_actual_attempts():
    """Compute average attempts directly from raw experimental data."""
    data = _load_all_raw_data()
    attempts = {}
    for approach in APPROACHES:
        if approach not in data:
            attempts[approach] = 0
            continue
        df = data[approach]
        attempts[approach] = df['attempts'].mean()
    return attempts


ACTUAL_ATTEMPTS = load_actual_attempts()


def load_actual_violations():
    """Compute average constraint violations directly from raw experimental data."""
    data = _load_all_raw_data()
    violations = {}
    for approach in APPROACHES:
        if approach not in data:
            violations[approach] = 0
            continue
        df = data[approach]
        if 'total_violations' in df.columns:
            violations[approach] = df['total_violations'].mean()
        else:
            violations[approach] = 0
    return violations


ACTUAL_VIOLATIONS = load_actual_violations()


def load_actual_search_space_reduction():
    """Compute first-round search space reduction directly from raw data.

    Normalises to percentage scale (0-100). Pure Random is set to 0.
    """
    data = _load_all_raw_data()
    reductions = {}
    for approach in APPROACHES:
        if approach == 'Pure Random':
            reductions[approach] = 0
            continue
        if approach not in data:
            reductions[approach] = 0
            continue
        df = data[approach]
        if 'reduction_rate_1' not in df.columns:
            reductions[approach] = 0
            continue
        val = df['reduction_rate_1'].mean()
        # Normalise: if stored as fraction (0-1), convert to percentage
        if val <= 1.0:
            val = val * 100
        reductions[approach] = val
    return reductions


ACTUAL_SEARCH_REDUCTION = load_actual_search_space_reduction()


def load_hamming_trajectories():
    """Load Hamming distance trajectories by round from raw data."""
    data = _load_all_raw_data()
    trajectories = {}
    for approach in APPROACHES:
        if approach not in data:
            trajectories[approach] = []
            continue
        df = data[approach]
        trajectory = []
        for i in range(1, 7):
            col = f'hamming_{i}'
            if col in df.columns:
                trajectory.append(df[col].mean())
            else:
                trajectory.append(np.nan)
        trajectories[approach] = trajectory
    return trajectories


HAMMING_TRAJECTORIES = load_hamming_trajectories()


def load_convergence_rates():
    """Compute convergence rate from raw data: (hamming_1 - hamming_final) / avg_rounds.

    Divides by the approach's average number of rounds, not per-game rounds.
    For winners, hamming_final = 0. For losers, hamming_final = last non-NaN hamming.
    """
    data = _load_all_raw_data()
    rates = {}
    for approach in APPROACHES:
        if approach not in data:
            rates[approach] = 0
            continue
        df = data[approach]
        if 'hamming_1' not in df.columns:
            rates[approach] = 0
            continue
        h1 = df['hamming_1'].values.astype(float)
        won_col = 'won' if 'won' in df.columns else 'win'
        won = df[won_col].values.astype(float)
        attempts = df['attempts'].values.astype(float)

        n = len(df)
        h_final = np.zeros(n, dtype=float)
        for i in range(n):
            if won[i] < 0.5:  # loser
                for r in range(6, 0, -1):
                    col = f'hamming_{r}'
                    if col in df.columns and not np.isnan(df[col].values[i]):
                        h_final[i] = df[col].values[i]
                        break

        # Use approach's average rounds as divisor
        rounds_played = np.where(won > 0.5, attempts, 6.0)
        avg_rounds = max(np.mean(rounds_played), 1.0)

        conv = (h1 - h_final) / avg_rounds
        rates[approach] = np.nanmean(conv)
    return rates


CONVERGENCE_RATES = load_convergence_rates()

# ============================================================================
# LEGACY DATA (kept for reference)
# ============================================================================

# 1. Algorithm results (standalone)
algorithms = {
    "CSS (Minimax)": ACTUAL_WIN_RATES['CSS'],  # True CSS / minimax regret
    "VOI": ACTUAL_WIN_RATES['VOI'],
    "Random": ACTUAL_WIN_RATES['Random'],
    "Pure Random": ACTUAL_WIN_RATES['Pure Random'],
}

# 2. Pure LLM results (best performing prompt type per model)
# Organized by parameter size category
llm_results = {
    # Small models (7-8B)
    "mistral-7b": {"win_rate": 98.0, "params": "7B", "category": "Small (7-8B)"},
    "granite-3.3-8b": {"win_rate": 96.0, "params": "8B", "category": "Small (7-8B)"},
    "llama-3.1-8b": {"win_rate": 93.0, "params": "8B", "category": "Small (7-8B)"},
    "nemotron-nano-8B": {"win_rate": 93.0, "params": "8B", "category": "Small (7-8B)"},

    # Medium models (20-27B)
    "gpt-oss-20b": {"win_rate": 96.0, "params": "20B", "category": "Medium (20-27B)"},
    "codestral-22b": {"win_rate": 95.0, "params": "22B", "category": "Medium (20-27B)"},
    "gemma-3-27b": {"win_rate": 99.0, "params": "27B", "category": "Medium (20-27B)"},

    # Large models (70B+)
    "llama-3.1-70b": {"win_rate": 96.0, "params": "70B", "category": "Large (70B+)"},
    "llama-3.3-70b": {"win_rate": 95.0, "params": "70B", "category": "Large (70B+)"},
    "gpt-oss-120b": {"win_rate": 92.0, "params": "120B", "category": "Large (70B+)"},
    "mistral-small-3.1": {"win_rate": 100.0, "params": "~22B", "category": "Medium (20-27B)"},
}

# 3. Hybrid results (LLM + CSS True)
hybrid_css_results = {
    "mistral-7b + CSS": 99.0,
    "granite-3.3-8b + CSS": 98.0,
    "codestral-22b + CSS": 97.0,
    "gemma-3-27b + CSS": 97.0,
    "llama-3.1-8b + CSS": 95.0,
    "llama-3.3-70b + CSS": 93.0,
}

# 4. Hybrid results (LLM + VOI)
hybrid_voi_results = {
    "nemotron-nano + VOI": 98.0,
    "mistral-small + VOI": 98.0,
    "llama-3.1-8b + VOI": 96.0,
    "llama-3.1-70b + VOI": 95.0,
    "mistral-7b + VOI": 95.0,
    "codestral-22b + VOI": 94.0,
    "gemma-3-27b + VOI": 94.0,
    "llama-3.3-70b + VOI": 92.0,
    "granite-3.3-8b + VOI": 92.0,
}

# 5. Hybrid results (LLM + Random)
hybrid_random_results = {
    "codestral-22b + Random": 98.0,
    "gemma-3-27b + Random": 95.0,
    "granite-3.3-8b + Random": 93.0,
    "mistral-small + Random": 93.0,
    "llama-3.3-70b + Random": 92.0,
    "nemotron-nano + Random": 92.0,
    "mistral-7b + Random": 91.0,
    "llama-3.1-8b + Random": 90.0,
    "llama-3.1-70b + Random": 88.0,
}

# ============================================================================
# GRAPH 0: Simple Win Rate Comparison (User Requested)
# Categories: Pure Random, Random, VOI, CSS, Small LLM, Mid LLM, Frontier LLM, Hybrid
# ============================================================================

def create_win_rate_comparison():
    """
    Create the main win rate comparison bar chart.
    Shows: Pure Random, Random, VOI, CSS (True), Small/Mid/Frontier LLMs, Hybrid
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Define categories and values in the requested order
    categories = [
        ('Pure Random', ACTUAL_WIN_RATES['Pure Random'], '#d62728'),    # Red - baseline
        ('Constraint\nRandom', ACTUAL_WIN_RATES['Random'], '#ff7f0e'),              # Orange
        ('VOI', ACTUAL_WIN_RATES['VOI'], '#2ca02c'),                    # Green - classic
        ('CSS', ACTUAL_WIN_RATES['CSS'], '#1f77b4'),                    # Blue - classic
        ('Small LLM\n(≤10B)', ACTUAL_WIN_RATES['Small_LLM'], '#9467bd'),    # Purple
        ('Mid LLM\n(10-30B)', ACTUAL_WIN_RATES['Mid_LLM'], '#8c564b'),      # Brown
        ('Frontier LLM\n(>30B)', ACTUAL_WIN_RATES['Frontier_LLM'], '#e377c2'),  # Pink
        ('Hybrid', ACTUAL_WIN_RATES['Hybrid'], '#7f7f7f'),              # Gray
    ]

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    # Create bars
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8, width=0.7)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        # Position label above bar
        ax.annotate(f'{val:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold')

    # Customize axes
    ax.set_xlabel('Approach', fontsize=13, fontweight='bold')
    ax.set_ylabel('Win Rate (%)', fontsize=13, fontweight='bold')
    ax.set_title('Win Rate Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 115)

    # Add horizontal reference lines
    ax.axhline(y=100, color='gray', linestyle='--', linewidth=1, alpha=0.5, label='Perfect (100%)')
    ax.axhline(y=ACTUAL_WIN_RATES['CSS'], color='#1f77b4', linestyle=':', linewidth=1, alpha=0.5)

    # Add category group brackets/annotations
    ax.annotate('Baselines', xy=(0.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Classical', xy=(2.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('LLM Categories', xy=(5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Hybrid', xy=(7, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')

    # Add divider lines between groups
    ax.axvline(x=1.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=3.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=6.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "win_rate_comparison_true_css.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "win_rate_comparison_true_css.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'win_rate_comparison_true_css.png'}")
    print(f"Saved: {output_dir / 'win_rate_comparison_true_css.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 0b: Average Attempts Comparison (User Requested)
# Categories: Pure Random, Random, VOI, CSS, Small LLM, Mid LLM, Frontier LLM, Hybrid
# ============================================================================

def create_attempts_comparison():
    """
    Create the average attempts comparison bar chart.
    Shows: Pure Random, Random, VOI, CSS (True), Small/Mid/Frontier LLMs, Hybrid
    Lower is better for this metric.
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Define categories and values in the requested order
    categories = [
        ('Pure Random', ACTUAL_ATTEMPTS['Pure Random'], '#d62728'),    # Red - baseline
        ('Constraint\nRandom', ACTUAL_ATTEMPTS['Random'], '#ff7f0e'),              # Orange
        ('VOI', ACTUAL_ATTEMPTS['VOI'], '#2ca02c'),                    # Green - classical
        ('CSS', ACTUAL_ATTEMPTS['CSS'], '#1f77b4'),                    # Blue - classical
        ('Small LLM\n(≤10B)', ACTUAL_ATTEMPTS['Small_LLM'], '#9467bd'),    # Purple
        ('Mid LLM\n(10-30B)', ACTUAL_ATTEMPTS['Mid_LLM'], '#8c564b'),      # Brown
        ('Frontier LLM\n(>30B)', ACTUAL_ATTEMPTS['Frontier_LLM'], '#e377c2'),  # Pink
        ('Hybrid', ACTUAL_ATTEMPTS['Hybrid'], '#7f7f7f'),              # Gray
    ]

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    # Create bars
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8, width=0.7)

    # Add value labels on bars (display with 2 decimal places)
    for bar, val in zip(bars, values):
        height = bar.get_height()
        # Position label above bar
        ax.annotate(f'{val:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold')

    # Customize axes
    ax.set_xlabel('Approach', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Attempts to Solve', fontsize=13, fontweight='bold')
    ax.set_title('Average Attempts Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylim(0, 8)

    # Add horizontal reference line at optimal (theoretical minimum ~3.5)
    ax.axhline(y=ACTUAL_ATTEMPTS['CSS'], color='#1f77b4', linestyle=':', linewidth=1, alpha=0.5)

    # Add category group annotations
    ax.annotate('Baselines', xy=(0.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Classical', xy=(2.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('LLM Categories', xy=(5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Hybrid', xy=(7, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')

    # Add divider lines between groups
    ax.axvline(x=1.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=3.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=6.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Add note that lower is better
    ax.annotate('↓ Lower is better', xy=(0.98, 0.95), xycoords='axes fraction',
                fontsize=10, ha='right', va='top', style='italic', color='#666666')

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "attempts_comparison_true_css.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "attempts_comparison_true_css.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'attempts_comparison_true_css.png'}")
    print(f"Saved: {output_dir / 'attempts_comparison_true_css.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 0c: Constraint Violations Comparison (User Requested)
# Categories: Pure Random, Random, VOI, CSS, Small LLM, Mid LLM, Frontier LLM, Hybrid
# ============================================================================

def create_violations_comparison():
    """
    Create the constraint violations comparison bar chart.
    Shows: Pure Random, Random, VOI, CSS (True), Small/Mid/Frontier LLMs, Hybrid
    Lower is better for this metric (0 = perfect constraint compliance).
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Define categories and values
    categories = [
        ('Pure Random', ACTUAL_VIOLATIONS['Pure Random'], '#d62728'),    # Red - baseline
        ('Constraint\nRandom', ACTUAL_VIOLATIONS['Random'], '#ff7f0e'),              # Orange - baseline
        ('VOI', ACTUAL_VIOLATIONS['VOI'], '#2ca02c'),                    # Green - classical
        ('CSS', ACTUAL_VIOLATIONS['CSS'], '#1f77b4'),                    # Blue - classical
        ('Small LLM\n(≤10B)', ACTUAL_VIOLATIONS['Small_LLM'], '#9467bd'),    # Purple
        ('Mid LLM\n(10-30B)', ACTUAL_VIOLATIONS['Mid_LLM'], '#8c564b'),      # Brown
        ('Frontier LLM\n(>30B)', ACTUAL_VIOLATIONS['Frontier_LLM'], '#e377c2'),  # Pink
        ('Hybrid', ACTUAL_VIOLATIONS['Hybrid'], '#7f7f7f'),              # Gray
    ]

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    # Create bars
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8, width=0.7)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        # Position label above bar (handle zero values)
        y_pos = max(height, 0.01)
        ax.annotate(f'{val:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, y_pos),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold')

    # Customize axes
    ax.set_xlabel('Approach', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Constraint Violations per Game', fontsize=13, fontweight='bold')
    ax.set_title('Constraint Violations Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)

    # Set y-axis limit to accommodate Pure Random (~20.67)
    ax.set_ylim(0, 24)

    # Add category group annotations (8 categories with Pure Random)
    ax.annotate('Baselines', xy=(0.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Classical', xy=(2.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('LLM Categories', xy=(5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Hybrid', xy=(7, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')

    # Add divider lines between groups (8 categories)
    ax.axvline(x=1.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=3.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=6.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Add note that lower is better
    ax.annotate('↓ Lower is better (0 = perfect)', xy=(0.98, 0.95), xycoords='axes fraction',
                fontsize=10, ha='right', va='top', style='italic', color='#666666')

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "violations_comparison_true_css.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "violations_comparison_true_css.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'violations_comparison_true_css.png'}")
    print(f"Saved: {output_dir / 'violations_comparison_true_css.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 0d: Search Space Reduction Comparison (User Requested)
# Categories: Pure Random, Random, VOI, CSS, Small LLM, Mid LLM, Frontier LLM, Hybrid
# ============================================================================

def create_search_space_reduction_comparison():
    """
    Create the search space reduction comparison bar chart.
    Shows first-round reduction: Random, VOI, CSS (True), Small/Mid/Frontier LLMs, Hybrid
    Higher is better (more candidates eliminated = more information gained).
    Note: Pure Random excluded because it doesn't use the reduced search space.
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Define categories and values in the requested order
    # Pure Random set to 0 - it calculates reduction but never uses it (0% win rate, 20+ violations)
    categories = [
        ('Pure Random', 0, '#d62728'),                                         # Red - set to 0
        ('Constraint\nRandom', ACTUAL_SEARCH_REDUCTION['Random'], '#ff7f0e'),              # Orange - baseline
        ('VOI', ACTUAL_SEARCH_REDUCTION['VOI'], '#2ca02c'),                    # Green - classical
        ('CSS', ACTUAL_SEARCH_REDUCTION['CSS'], '#1f77b4'),                    # Blue - classical
        ('Small LLM\n(≤10B)', ACTUAL_SEARCH_REDUCTION['Small_LLM'], '#9467bd'),    # Purple
        ('Mid LLM\n(10-30B)', ACTUAL_SEARCH_REDUCTION['Mid_LLM'], '#8c564b'),      # Brown
        ('Frontier LLM\n(>30B)', ACTUAL_SEARCH_REDUCTION['Frontier_LLM'], '#e377c2'),  # Pink
        ('Hybrid', ACTUAL_SEARCH_REDUCTION['Hybrid'], '#7f7f7f'),              # Gray
    ]

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    # Create bars
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8, width=0.7)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.annotate(f'{val:.1f}%',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=11, fontweight='bold')

    # Customize axes
    ax.set_xlabel('Approach', fontsize=13, fontweight='bold')
    ax.set_ylabel('First-Round Search Space Reduction (%)', fontsize=13, fontweight='bold')
    ax.set_title('Search Space Reduction Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)

    # Set y-axis to start from 0 for accurate representation, with room for labels
    ax.set_ylim(0, 105)

    # Add horizontal reference line at CSS performance
    ax.axhline(y=ACTUAL_SEARCH_REDUCTION['CSS'], color='#1f77b4', linestyle=':', linewidth=1, alpha=0.5)

    # Add category group annotations (8 categories with Pure Random)
    ax.annotate('Baselines', xy=(0.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Classical', xy=(2.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('LLM Categories', xy=(5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Hybrid', xy=(7, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')

    # Add divider lines between groups (8 categories)
    ax.axvline(x=1.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=3.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=6.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "search_space_reduction_comparison.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "search_space_reduction_comparison.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'search_space_reduction_comparison.png'}")
    print(f"Saved: {output_dir / 'search_space_reduction_comparison.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 0e: Hamming Distance Convergence Trajectories (User Requested)
# Shows how each approach converges to the target word across rounds
# ============================================================================

def create_hamming_convergence_graph():
    """
    Create line graph showing Hamming distance trajectories across rounds.
    Shows convergence behavior: how quickly each approach gets closer to the answer.
    Lower values = closer to correct solution.
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    rounds = [1, 2, 3, 4, 5, 6]

    # Define line styles and colors for each approach
    approaches = [
        ('Pure Random', HAMMING_TRAJECTORIES['Pure Random'], '#d62728', 'x', '--'),    # Red dashed
        ('Constraint Random', HAMMING_TRAJECTORIES['Random'], '#ff7f0e', 's', '-'),               # Orange solid
        ('VOI', HAMMING_TRAJECTORIES['VOI'], '#2ca02c', '^', '-'),                     # Green solid
        ('CSS', HAMMING_TRAJECTORIES['CSS'], '#1f77b4', 'o', '-'),                     # Blue solid
        ('Small LLM (≤10B)', HAMMING_TRAJECTORIES['Small_LLM'], '#9467bd', 'D', '-'),  # Purple solid
        ('Mid LLM (10-30B)', HAMMING_TRAJECTORIES['Mid_LLM'], '#8c564b', 'p', '-'),    # Brown solid
        ('Frontier LLM (>30B)', HAMMING_TRAJECTORIES['Frontier_LLM'], '#e377c2', 'h', '-'),  # Pink solid
        ('Hybrid', HAMMING_TRAJECTORIES['Hybrid'], '#7f7f7f', '*', '-'),               # Gray solid
    ]

    # Plot each approach
    for name, trajectory, color, marker, linestyle in approaches:
        if trajectory and len(trajectory) > 0:
            # Handle NaN values by only plotting valid points
            valid_rounds = []
            valid_values = []
            for r, v in zip(rounds, trajectory):
                if not np.isnan(v):
                    valid_rounds.append(r)
                    valid_values.append(v)

            ax.plot(valid_rounds, valid_values, color=color, marker=marker,
                    linestyle=linestyle, linewidth=2, markersize=8, label=name)

    # Customize axes
    ax.set_xlabel('Round', fontsize=13, fontweight='bold')
    ax.set_ylabel('Average Hamming Distance to Target', fontsize=13, fontweight='bold')
    ax.set_title('Hamming Distance by Round',
                 fontsize=14, fontweight='bold')

    ax.set_xticks(rounds)
    ax.set_xlim(0.5, 6.5)
    ax.set_ylim(0, 5.5)

    # Add legend
    ax.legend(loc='upper right', fontsize=9, framealpha=0.9)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.xaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Add annotation
    ax.annotate('↓ Lower is better (0 = solved)', xy=(0.02, 0.02), xycoords='axes fraction',
                fontsize=10, ha='left', va='bottom', style='italic', color='#666666')

    # Add note about N
    ax.annotate('N=100 games per approach', xy=(0.98, 0.02), xycoords='axes fraction',
                fontsize=9, ha='right', va='bottom', style='italic', color='#999999')

    # Adjust layout
    plt.tight_layout()

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "hamming_convergence_trajectories.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "hamming_convergence_trajectories.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'hamming_convergence_trajectories.png'}")
    print(f"Saved: {output_dir / 'hamming_convergence_trajectories.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 0f: Convergence Rate Comparison (User Requested)
# Shows how fast each approach decreases Hamming distance per round
# ============================================================================

def create_convergence_rate_comparison():
    """
    Create bar chart showing convergence rate (Hamming distance decrease per round).
    Higher values = faster convergence to the solution.
    """
    # Set up the figure
    fig, ax = plt.subplots(figsize=(12, 7))

    # Define categories and values in the requested order
    # Note: Pure Random set to 0 (actual value is ~-0.01 which is effectively no convergence)
    categories = [
        ('Pure Random', 0, '#d62728'),                                   # Red - baseline, set to 0
        ('Constraint\nRandom', CONVERGENCE_RATES['Random'], '#ff7f0e'),              # Orange
        ('VOI', CONVERGENCE_RATES['VOI'], '#2ca02c'),                    # Green - classic
        ('CSS', CONVERGENCE_RATES['CSS'], '#1f77b4'),                    # Blue - classic
        ('Small LLM\n(≤10B)', CONVERGENCE_RATES['Small_LLM'], '#9467bd'),    # Purple
        ('Mid LLM\n(10-30B)', CONVERGENCE_RATES['Mid_LLM'], '#8c564b'),      # Brown
        ('Frontier LLM\n(>30B)', CONVERGENCE_RATES['Frontier_LLM'], '#e377c2'),  # Pink
        ('Hybrid', CONVERGENCE_RATES['Hybrid'], '#7f7f7f'),              # Gray
    ]

    labels = [c[0] for c in categories]
    values = [c[1] for c in categories]
    colors = [c[2] for c in categories]

    # Create bars
    x = np.arange(len(labels))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.8, width=0.7)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        height = bar.get_height()
        # Handle negative values (Pure Random)
        if height < 0:
            va = 'top'
            offset = -5
        else:
            va = 'bottom'
            offset = 5
        ax.annotate(f'{val:.2f}',
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, offset),
                    textcoords="offset points",
                    ha='center', va=va,
                    fontsize=11, fontweight='bold')

    # Customize axes
    ax.set_xlabel('Approach', fontsize=13, fontweight='bold')
    ax.set_ylabel('Convergence Rate', fontsize=13, fontweight='bold')
    ax.set_title('Convergence Rate Comparison',
                 fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)

    # Set y-axis limits to accommodate new values above 1.0
    max_val = max(values) * 1.15
    ax.set_ylim(0, max_val)

    # Add horizontal line at 0
    ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)

    # Add category group annotations
    ax.annotate('Baselines', xy=(0.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Classical', xy=(2.5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('LLM Categories', xy=(5, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')
    ax.annotate('Hybrid', xy=(7, -0.12), xycoords=('data', 'axes fraction'),
                fontsize=10, ha='center', style='italic', color='#666666')

    # Add divider lines between groups
    ax.axvline(x=1.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=3.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)
    ax.axvline(x=6.5, color='gray', linestyle='-', linewidth=0.5, alpha=0.3)

    # Grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Add note that higher is better
    ax.annotate('↑ Higher is better', xy=(0.98, 0.95), xycoords='axes fraction',
                fontsize=10, ha='right', va='top', style='italic', color='#666666')

    # Adjust layout
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.15)

    # Save figures
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)

    plt.savefig(output_dir / "convergence_rate_comparison.png", dpi=300, bbox_inches='tight')
    plt.savefig(output_dir / "convergence_rate_comparison.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'convergence_rate_comparison.png'}")
    print(f"Saved: {output_dir / 'convergence_rate_comparison.pdf'}")

    return fig, ax


# ============================================================================
# GRAPH 1: Main Comparison (Algorithms vs LLM Categories vs Hybrids)
# ============================================================================

def create_main_comparison():
    """Create main comparison bar chart."""
    fig, ax = plt.subplots(figsize=(14, 8))

    # Categories and their data
    categories = []
    values = []
    colors = []

    # Algorithms
    algo_names = ["CSS\n(Minimax)", "VOI", "Constraint\nRandom", "Pure\nRandom"]
    algo_values = [96.0, 99.0, 91.0, 0.0]
    categories.extend(algo_names)
    values.extend(algo_values)
    colors.extend(['#2ecc71', '#2ecc71', '#2ecc71', '#e74c3c'])  # Green, red for pure random

    # Spacer
    categories.append("")
    values.append(0)
    colors.append('white')

    # LLM Categories (average per category)
    small_llms = [v["win_rate"] for k, v in llm_results.items() if v["category"] == "Small (7-8B)"]
    medium_llms = [v["win_rate"] for k, v in llm_results.items() if v["category"] == "Medium (20-27B)"]
    large_llms = [v["win_rate"] for k, v in llm_results.items() if v["category"] == "Large (70B+)"]

    llm_cats = ["LLM\nSmall\n(7-8B)", "LLM\nMedium\n(20-27B)", "LLM\nLarge\n(70B+)"]
    llm_vals = [np.mean(small_llms), np.mean(medium_llms), np.mean(large_llms)]
    categories.extend(llm_cats)
    values.extend(llm_vals)
    colors.extend(['#3498db', '#3498db', '#3498db'])  # Blue

    # Spacer
    categories.append("")
    values.append(0)
    colors.append('white')

    # Hybrids (average per type)
    hybrid_cats = ["Hybrid\n(LLM+CSS)", "Hybrid\n(LLM+VOI)", "Hybrid\n(LLM+Random)"]
    hybrid_vals = [
        np.mean(list(hybrid_css_results.values())),
        np.mean(list(hybrid_voi_results.values())),
        np.mean(list(hybrid_random_results.values()))
    ]
    categories.extend(hybrid_cats)
    values.extend(hybrid_vals)
    colors.extend(['#9b59b6', '#9b59b6', '#9b59b6'])  # Purple

    # Create bars
    x = np.arange(len(categories))
    bars = ax.bar(x, values, color=colors, edgecolor='black', linewidth=0.5)

    # Add value labels on bars
    for bar, val in zip(bars, values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   f'{val:.1f}%', ha='center', va='bottom', fontsize=10, fontweight='bold')

    # Formatting
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Wordle Strategy Comparison: Win Rates', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontsize=9)
    ax.set_ylim(0, 110)
    ax.axhline(y=100, color='gray', linestyle='--', alpha=0.3)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='Algorithms'),
        Patch(facecolor='#e74c3c', edgecolor='black', label='Baseline (Pure Random)'),
        Patch(facecolor='#3498db', edgecolor='black', label='Pure LLMs'),
        Patch(facecolor='#9b59b6', edgecolor='black', label='Hybrids (LLM + Algorithm)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    # Add grid
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()

    # Save
    output_dir = RESULTS_DIR / "plots"
    output_dir.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_dir / "win_rate_comparison.png", dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "win_rate_comparison.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'win_rate_comparison.png'}")
    plt.close()

# ============================================================================
# GRAPH 2: Detailed LLM Comparison by Model
# ============================================================================

def create_llm_detail():
    """Create detailed LLM comparison."""
    fig, ax = plt.subplots(figsize=(12, 6))

    # Sort by win rate
    sorted_llms = sorted(llm_results.items(), key=lambda x: x[1]['win_rate'], reverse=True)

    names = [k for k, v in sorted_llms]
    win_rates = [v['win_rate'] for k, v in sorted_llms]
    categories = [v['category'] for k, v in sorted_llms]

    # Color by category
    color_map = {
        "Small (7-8B)": '#e74c3c',
        "Medium (20-27B)": '#f39c12',
        "Large (70B+)": '#27ae60'
    }
    colors = [color_map[c] for c in categories]

    # Create bars
    x = np.arange(len(names))
    bars = ax.bar(x, win_rates, color=colors, edgecolor='black', linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, win_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
               f'{val:.0f}%', ha='center', va='bottom', fontsize=9, fontweight='bold')

    # Formatting
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Pure LLM Win Rates by Model', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=9)
    ax.set_ylim(0, 110)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#e74c3c', edgecolor='black', label='Small (7-8B)'),
        Patch(facecolor='#f39c12', edgecolor='black', label='Medium (20-27B)'),
        Patch(facecolor='#27ae60', edgecolor='black', label='Large (70B+)'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()

    output_dir = RESULTS_DIR / "plots"
    plt.savefig(output_dir / "llm_win_rates_detail.png", dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "llm_win_rates_detail.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'llm_win_rates_detail.png'}")
    plt.close()

# ============================================================================
# GRAPH 3: Hybrid Comparison
# ============================================================================

def create_hybrid_comparison():
    """Create hybrid strategy comparison."""
    fig, ax = plt.subplots(figsize=(14, 6))

    # Combine all hybrids
    all_hybrids = {}
    for k, v in hybrid_css_results.items():
        all_hybrids[k] = {"win_rate": v, "type": "CSS"}
    for k, v in hybrid_voi_results.items():
        all_hybrids[k] = {"win_rate": v, "type": "VOI"}
    for k, v in hybrid_random_results.items():
        all_hybrids[k] = {"win_rate": v, "type": "Random"}

    # Sort by win rate
    sorted_hybrids = sorted(all_hybrids.items(), key=lambda x: x[1]['win_rate'], reverse=True)

    names = [k for k, v in sorted_hybrids]
    win_rates = [v['win_rate'] for k, v in sorted_hybrids]
    types = [v['type'] for k, v in sorted_hybrids]

    # Color by type
    color_map = {"CSS": '#2ecc71', "VOI": '#3498db', "Random": '#e74c3c'}
    colors = [color_map[t] for t in types]

    # Create bars
    x = np.arange(len(names))
    bars = ax.bar(x, win_rates, color=colors, edgecolor='black', linewidth=0.5)

    # Add value labels
    for bar, val in zip(bars, win_rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
               f'{val:.0f}%', ha='center', va='bottom', fontsize=8, fontweight='bold')

    # Formatting
    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Hybrid Strategy Win Rates (LLM + Algorithm)', fontsize=14, fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right', fontsize=8)
    ax.set_ylim(0, 110)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2ecc71', edgecolor='black', label='LLM + CSS'),
        Patch(facecolor='#3498db', edgecolor='black', label='LLM + VOI'),
        Patch(facecolor='#e74c3c', edgecolor='black', label='LLM + Random'),
    ]
    ax.legend(handles=legend_elements, loc='lower right', fontsize=10)

    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()

    output_dir = RESULTS_DIR / "plots"
    plt.savefig(output_dir / "hybrid_win_rates.png", dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "hybrid_win_rates.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'hybrid_win_rates.png'}")
    plt.close()

# ============================================================================
# GRAPH 4: Summary Box Plot
# ============================================================================

def create_summary_boxplot():
    """Create summary box plot comparing all categories."""
    fig, ax = plt.subplots(figsize=(10, 6))

    # Prepare data for boxplot
    data = [
        [96.0, 99.0, 91.0],  # Algorithms (CSS, VOI, Random) - excluding pure random
        [v["win_rate"] for v in llm_results.values()],  # All LLMs
        list(hybrid_css_results.values()),  # CSS Hybrids
        list(hybrid_voi_results.values()),  # VOI Hybrids
        list(hybrid_random_results.values()),  # Random Hybrids
    ]

    labels = ['Algorithms\n(CSS, VOI, Random)', 'Pure LLMs', 'LLM + CSS\nHybrids',
              'LLM + VOI\nHybrids', 'LLM + Random\nHybrids']

    colors = ['#2ecc71', '#3498db', '#9b59b6', '#9b59b6', '#9b59b6']

    bp = ax.boxplot(data, labels=labels, patch_artist=True)

    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    # Add individual points
    for i, d in enumerate(data):
        x = np.random.normal(i+1, 0.04, size=len(d))
        ax.scatter(x, d, alpha=0.6, color='black', s=20, zorder=3)

    ax.set_ylabel('Win Rate (%)', fontsize=12)
    ax.set_title('Win Rate Distribution by Strategy Category', fontsize=14, fontweight='bold')
    ax.set_ylim(85, 105)
    ax.yaxis.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    plt.tight_layout()

    output_dir = RESULTS_DIR / "plots"
    plt.savefig(output_dir / "win_rate_boxplot.png", dpi=150, bbox_inches='tight')
    plt.savefig(output_dir / "win_rate_boxplot.pdf", bbox_inches='tight')
    print(f"Saved: {output_dir / 'win_rate_boxplot.png'}")
    plt.close()

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    print("Creating comparison graphs...")
    print("=" * 50)

    # Print actual win rates being used
    print("\nActual Win Rates (from data files):")
    print("-" * 40)
    for k, v in ACTUAL_WIN_RATES.items():
        print(f"  {k}: {v:.1f}%")
    print("-" * 40)

    # Create the main requested graph
    print("\nCreating win rate comparison graph...")
    create_win_rate_comparison()

    # Create attempts comparison graph
    print("\nCreating attempts comparison graph...")
    create_attempts_comparison()

    # Create violations comparison graph
    print("\nCreating violations comparison graph...")
    create_violations_comparison()

    # Create search space reduction comparison graph
    print("\nCreating search space reduction comparison graph...")
    create_search_space_reduction_comparison()

    # Create hamming convergence graph
    print("\nCreating hamming convergence graph...")
    create_hamming_convergence_graph()

    # Create convergence rate comparison graph
    print("\nCreating convergence rate comparison graph...")
    create_convergence_rate_comparison()

    # Create additional graphs
    print("\nCreating additional graphs...")
    create_main_comparison()
    create_llm_detail()
    create_hybrid_comparison()
    create_summary_boxplot()

    print("=" * 50)
    print("All graphs created successfully!")
    print(f"Output directory: {RESULTS_DIR / 'plots'}")
