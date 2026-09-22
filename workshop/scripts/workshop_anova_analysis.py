#!/usr/bin/env python3
"""
ANOVA Analysis for Workshop Paper: Hybrid Degradation

Compares 5 approaches:
1. CSS (pure algorithm - minimax regret)
2. VOI (pure algorithm - value of information)
3. Hybrid LLM-First (LLM starts, then algorithm)
4. Hybrid Algo-First (Algorithm starts, then LLM)
5. Hybrid Alternating (alternates each round)

Metrics analyzed:
1. Win Rate
2. Attempts
3. Convergence Rate
4. Average Hamming Distance
5. Reduction Rate (first round)
6. Constraint Violations
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("Warning: statsmodels not installed - Tukey HSD will be skipped")

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR = Path(__file__).parent
WORKSHOP_DIR = SCRIPT_DIR.parent
PROJECT_DIR = WORKSHOP_DIR.parent
RESULTS_DIR = WORKSHOP_DIR / "results_css"
RESULTS_OLD_DIR = WORKSHOP_DIR / "results_old_css"
ALGO_DATA = PROJECT_DIR / "results/algorithms"
OUTPUT_DIR = WORKSHOP_DIR / "statistical_analysis"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def categorize_config(config_name):
    """Categorize config as LLM-first, Algorithm-first, or Alternating."""
    config = config_name.lower()

    # LLM-first patterns
    if config.startswith('l_to') or config.startswith('l1_to') or \
       config.startswith('l2_to') or config.startswith('l3_to') or \
       'llm_first' in config:
        return 'Hybrid_LLM_First'

    # True alternating patterns
    if config.startswith('alt_css') or config.startswith('alt_voi') or \
       config.startswith('alternating_algorithm') or config.startswith('old_alternating'):
        return 'Hybrid_Alternating'

    # Algo-first patterns
    if config.startswith('c_to') or config.startswith('v_to') or \
       ('css' in config and '_to_l' in config) or \
       ('voi' in config and '_to_l' in config) or \
       (config.startswith('rerank_css') and 'llm_first' not in config) or \
       (config.startswith('rerank_voi') and 'llm_first' not in config) or \
       config.startswith('constraint_filter'):
        return 'Hybrid_Algo_First'

    return None


def load_pure_algorithms():
    """Load CSS and VOI algorithm data."""
    all_data = []

    # CSS
    css_file = ALGO_DATA / "css/css_results_with_candidates.csv"
    if css_file.exists():
        df = pd.read_csv(css_file)
        df['approach'] = 'CSS'
        df['total_violations'] = 0  # Algorithms have 0 violations
        all_data.append(df)
        print(f"  CSS: {len(df)} games")

    # VOI
    algo_file = ALGO_DATA / "raw data/algorithm_results_with_candidates.csv"
    if algo_file.exists():
        df = pd.read_csv(algo_file)
        voi_df = df[df['strategy'] == 'voi'].copy()
        voi_df['approach'] = 'VOI'
        voi_df['total_violations'] = 0
        all_data.append(voi_df)
        print(f"  VOI: {len(voi_df)} games")

    return pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()


def load_hybrid_data():
    """Load hybrid data from workshop results."""
    all_data = []

    # Load from new CSS results
    for csv_file in RESULTS_DIR.rglob("*.csv"):
        if csv_file.name.startswith("summary"):
            continue
        try:
            df = pd.read_csv(csv_file)
            category = categorize_config(csv_file.stem)
            if category:
                df['approach'] = category
                all_data.append(df)
        except Exception as e:
            print(f"  Error loading {csv_file}: {e}")

    # Load alternating from old CSS results
    old_group_c = RESULTS_OLD_DIR / "group_c"
    if old_group_c.exists():
        for csv_file in old_group_c.rglob("*.csv"):
            if csv_file.name.startswith("summary"):
                continue
            try:
                df = pd.read_csv(csv_file)
                df['approach'] = 'Hybrid_Alternating'
                all_data.append(df)
            except Exception as e:
                print(f"  Error loading {csv_file}: {e}")

    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        for approach in combined['approach'].unique():
            count = len(combined[combined['approach'] == approach])
            print(f"  {approach}: {count} games")
        return combined
    return pd.DataFrame()


def calculate_convergence_rate(row):
    """Calculate convergence rate for a single game."""
    # Get hamming distances
    distances = []
    for r in range(1, 7):
        col = f'hamming_{r}'
        if col in row.index and pd.notna(row[col]):
            distances.append(row[col])
        else:
            break

    if len(distances) < 2:
        return np.nan

    initial = distances[0]
    final = distances[-1]
    num_rounds = len(distances)

    return (initial - final) / num_rounds


def calculate_avg_hamming(row):
    """Calculate average Hamming distance across all rounds for a single game."""
    distances = []
    for r in range(1, 7):
        col = f'hamming_{r}'
        if col in row.index and pd.notna(row[col]):
            distances.append(row[col])
        else:
            break

    if len(distances) == 0:
        return np.nan

    return sum(distances) / len(distances)


def prepare_data(df):
    """Prepare data with all required metrics."""
    # Ensure win rate column
    if 'won' in df.columns:
        df['win_rate'] = df['won'].astype(float)

    # Calculate convergence rate if not present
    if 'convergence_rate' not in df.columns:
        df['convergence_rate'] = df.apply(calculate_convergence_rate, axis=1)

    # Calculate average Hamming distance if not present
    if 'avg_hamming' not in df.columns:
        df['avg_hamming'] = df.apply(calculate_avg_hamming, axis=1)

    # Ensure total_violations column
    if 'total_violations' not in df.columns:
        df['total_violations'] = 0

    return df


# =============================================================================
# ANOVA FUNCTIONS
# =============================================================================

def run_anova_for_metric(df, metric_name, metric_col, lower_is_better=True):
    """Run one-way ANOVA and post-hoc tests for a single metric."""
    print(f"\n{'='*80}")
    print(f"ANOVA: {metric_name.upper()}")
    print(f"{'='*80}")

    # Remove rows with missing values
    df_clean = df.dropna(subset=[metric_col])

    if len(df_clean) == 0:
        print(f"No data available for {metric_name}")
        return None

    approaches = sorted(df_clean['approach'].unique())

    # Descriptive statistics
    print(f"\n--- Descriptive Statistics ---")
    desc = df_clean.groupby('approach')[metric_col].agg(['count', 'mean', 'std', 'min', 'max'])
    desc = desc.sort_values('mean', ascending=lower_is_better)
    print(desc.round(4).to_string())

    # One-way ANOVA
    groups = [df_clean[df_clean['approach'] == app][metric_col].values for app in approaches]
    f_stat, p_value = stats.f_oneway(*groups)

    # Effect size (eta-squared)
    grand_mean = df_clean[metric_col].mean()
    ss_total = ((df_clean[metric_col] - grand_mean) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    eta_squared = ss_between / ss_total if ss_total > 0 else 0

    print(f"\n--- One-Way ANOVA ---")
    print(f"F({len(approaches)-1}, {len(df_clean)-len(approaches)}) = {f_stat:.4f}")
    print(f"p-value: {p_value:.2e}")
    print(f"Eta-squared (η²): {eta_squared:.4f}")

    effect = "large" if eta_squared >= 0.14 else "medium" if eta_squared >= 0.06 else "small" if eta_squared >= 0.01 else "negligible"
    print(f"Effect size: {effect}")

    sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"
    print(f"Significance: {sig}")

    # Tukey HSD post-hoc test
    tukey_results = None
    if HAS_STATSMODELS and p_value < 0.05:
        print(f"\n--- Post-hoc Tukey HSD ---")
        try:
            tukey = pairwise_tukeyhsd(df_clean[metric_col], df_clean['approach'], alpha=0.05)
            print(tukey.summary())
            tukey_results = tukey
        except Exception as e:
            print(f"Tukey HSD error: {e}")
    elif p_value >= 0.05:
        print(f"\n--- Post-hoc Tests ---")
        print("Skipped (ANOVA not significant)")

    return {
        'metric': metric_name,
        'F': f_stat,
        'p': p_value,
        'eta_squared': eta_squared,
        'effect_size': effect,
        'significance': sig,
        'n_total': len(df_clean),
        'n_approaches': len(approaches),
        'descriptives': desc,
        'tukey': tukey_results
    }


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("="*80)
    print("WORKSHOP ANOVA ANALYSIS")
    print("Hybrid Degradation in LLM-Algorithm Systems")
    print("="*80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Load data
    print("\n--- Loading Data ---")

    print("\nPure Algorithms:")
    algo_data = load_pure_algorithms()

    print("\nHybrid Approaches:")
    hybrid_data = load_hybrid_data()

    # Combine all data
    if len(algo_data) > 0 and len(hybrid_data) > 0:
        df = pd.concat([algo_data, hybrid_data], ignore_index=True)
    elif len(algo_data) > 0:
        df = algo_data
    else:
        df = hybrid_data

    # Prepare data
    df = prepare_data(df)

    print(f"\n--- Combined Dataset ---")
    print(f"Total observations: {len(df)}")
    print(f"Approaches: {sorted(df['approach'].unique())}")

    # Store all results
    all_results = {}

    # Run ANOVA for each metric
    # 1. Win Rate
    if 'win_rate' in df.columns:
        all_results['win_rate'] = run_anova_for_metric(
            df, 'Win Rate', 'win_rate', lower_is_better=False
        )

    # 2. Attempts (only for won games)
    df_won = df[df['won'] == True].copy()
    if 'attempts' in df_won.columns and len(df_won) > 0:
        all_results['attempts'] = run_anova_for_metric(
            df_won, 'Attempts (when won)', 'attempts', lower_is_better=True
        )

    # 3. Convergence Rate
    if 'convergence_rate' in df.columns:
        all_results['convergence_rate'] = run_anova_for_metric(
            df, 'Convergence Rate', 'convergence_rate', lower_is_better=False
        )

    # 4. Average Hamming Distance
    if 'avg_hamming' in df.columns:
        all_results['avg_hamming'] = run_anova_for_metric(
            df, 'Average Hamming Distance', 'avg_hamming', lower_is_better=True
        )

    # 5. Reduction Rate (first round)
    if 'reduction_rate_1' in df.columns:
        all_results['reduction_rate'] = run_anova_for_metric(
            df, 'First-Round Reduction Rate', 'reduction_rate_1', lower_is_better=False
        )

    # 6. Constraint Violations
    if 'total_violations' in df.columns:
        all_results['violations'] = run_anova_for_metric(
            df, 'Constraint Violations', 'total_violations', lower_is_better=True
        )

    # ==========================================================================
    # SAVE RESULTS
    # ==========================================================================
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)

    # Generate summary report
    report_lines = [
        "="*80,
        "WORKSHOP ANOVA ANALYSIS - SUMMARY REPORT",
        "Hybrid Degradation in LLM-Algorithm Systems",
        "="*80,
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "APPROACHES COMPARED:",
        "-"*40,
        "1. CSS - Pure algorithm (minimax regret)",
        "2. VOI - Pure algorithm (value of information)",
        "3. Hybrid_LLM_First - LLM starts, then algorithm",
        "4. Hybrid_Algo_First - Algorithm starts, then LLM",
        "5. Hybrid_Alternating - Alternates each round",
        "",
        "="*80,
        "RESULTS SUMMARY",
        "="*80,
    ]

    summary_table = []
    for metric_name, result in all_results.items():
        if result is None:
            continue

        report_lines.append(f"\n{result['metric'].upper()}")
        report_lines.append(f"  F = {result['F']:.4f}, p = {result['p']:.2e}")
        report_lines.append(f"  η² = {result['eta_squared']:.4f} ({result['effect_size']})")
        report_lines.append(f"  Significance: {result['significance']}")

        summary_table.append({
            'Metric': result['metric'],
            'F': f"{result['F']:.2f}",
            'p-value': f"{result['p']:.2e}",
            'η²': f"{result['eta_squared']:.4f}",
            'Effect': result['effect_size'],
            'Sig': result['significance']
        })

    # Print summary table
    print("\n" + "-"*80)
    summary_df = pd.DataFrame(summary_table)
    print(summary_df.to_string(index=False))
    print("-"*80)

    # Key findings
    report_lines.extend([
        "",
        "="*80,
        "KEY FINDINGS",
        "="*80,
        "",
    ])

    # Check for significant differences
    for metric_name, result in all_results.items():
        if result and result['p'] < 0.05:
            report_lines.append(f"- {result['metric']}: Significant difference (p < .05)")

    report_lines.extend([
        "",
        "="*80,
        "INTERPRETATION",
        "="*80,
        "",
        "If violations show significant differences with Alternating highest,",
        "this supports the thesis that context-switching introduces state",
        "inconsistency that degrades logical reasoning.",
        "",
        "="*80,
        "END OF REPORT",
        "="*80
    ])

    report_text = "\n".join(report_lines)

    # Save report
    with open(OUTPUT_DIR / "workshop_anova_report.txt", 'w') as f:
        f.write(report_text)
    print(f"\nSaved: {OUTPUT_DIR / 'workshop_anova_report.txt'}")

    # Save combined data
    df.to_csv(OUTPUT_DIR / "workshop_combined_data.csv", index=False)
    print(f"Saved: {OUTPUT_DIR / 'workshop_combined_data.csv'}")

    print(f"\n✓ All results saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
