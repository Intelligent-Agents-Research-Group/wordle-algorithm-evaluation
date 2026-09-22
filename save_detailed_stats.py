#!/usr/bin/env python3
"""
Save Descriptive Statistics and Pairwise Comparisons as CSVs
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from itertools import combinations
import warnings
warnings.filterwarnings('ignore')

try:
    from statsmodels.stats.multicomp import pairwise_tukeyhsd
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False

# Load the combined data
BASE_DIR = Path("/Users/kevin/Desktop/wordle")
OUTPUT_DIR = BASE_DIR / "statistical_analysis_results" / "full_anova_stats"
DATA_FILE = OUTPUT_DIR / "combined_data.csv"

df = pd.read_csv(DATA_FILE)

print("Generating detailed statistics CSVs...")
print(f"Output directory: {OUTPUT_DIR}")

# =============================================================================
# DESCRIPTIVE STATISTICS
# =============================================================================

metrics = {
    'win_rate': {'col': 'won', 'name': 'Win Rate', 'lower_better': False},
    'attempts': {'col': 'attempts', 'name': 'Attempts', 'lower_better': True},
    'hamming_1': {'col': 'hamming_1', 'name': 'Hamming Distance (Round 1)', 'lower_better': True},
    'hamming_2': {'col': 'hamming_2', 'name': 'Hamming Distance (Round 2)', 'lower_better': True},
    'hamming_3': {'col': 'hamming_3', 'name': 'Hamming Distance (Round 3)', 'lower_better': True},
    'hamming_4': {'col': 'hamming_4', 'name': 'Hamming Distance (Round 4)', 'lower_better': True},
    'hamming_5': {'col': 'hamming_5', 'name': 'Hamming Distance (Round 5)', 'lower_better': True},
    'hamming_6': {'col': 'hamming_6', 'name': 'Hamming Distance (Round 6)', 'lower_better': True},
    'total_violations': {'col': 'total_violations', 'name': 'Constraint Violations', 'lower_better': True},
    'candidates_after_1': {'col': 'candidates_after_1', 'name': 'Search Space (Candidates After R1)', 'lower_better': True},
    'reduction_rate_1': {'col': 'reduction_rate_1', 'name': 'Search Space Reduction (Round 1)', 'lower_better': False},
    'convergence_rate': {'col': 'convergence_rate', 'name': 'Convergence Rate (Hamming/round)', 'lower_better': False},
}

# Create descriptive stats for all metrics
all_descriptive = []

for metric_id, metric_info in metrics.items():
    col = metric_info['col']
    if col not in df.columns:
        continue

    desc = df.groupby('approach')[col].agg(['count', 'mean', 'std', 'min', 'max', 'median'])
    desc['se'] = desc['std'] / np.sqrt(desc['count'])
    desc['ci_95'] = desc['se'] * 1.96
    desc = desc.reset_index()
    desc['metric'] = metric_info['name']
    desc['metric_id'] = metric_id

    # Sort by mean (ascending if lower is better, descending otherwise)
    desc = desc.sort_values('mean', ascending=metric_info['lower_better'])
    desc['rank'] = range(1, len(desc) + 1)

    all_descriptive.append(desc)

df_descriptive = pd.concat(all_descriptive, ignore_index=True)

# Reorder columns
col_order = ['metric', 'metric_id', 'approach', 'rank', 'count', 'mean', 'std', 'se', 'ci_95', 'median', 'min', 'max']
df_descriptive = df_descriptive[col_order]

# Save
df_descriptive.to_csv(OUTPUT_DIR / "descriptive_statistics_all_metrics.csv", index=False)
print(f"✓ Saved: descriptive_statistics_all_metrics.csv")

# Also save per-metric files
for metric_id, metric_info in metrics.items():
    metric_data = df_descriptive[df_descriptive['metric_id'] == metric_id]
    if len(metric_data) > 0:
        metric_data.to_csv(OUTPUT_DIR / f"descriptive_{metric_id}.csv", index=False)
        print(f"  ✓ Saved: descriptive_{metric_id}.csv")

# =============================================================================
# PAIRWISE COMPARISONS (Tukey HSD)
# =============================================================================

if HAS_STATSMODELS:
    all_pairwise = []

    for metric_id, metric_info in metrics.items():
        col = metric_info['col']
        if col not in df.columns:
            continue

        df_clean = df.dropna(subset=[col])
        if len(df_clean) == 0:
            continue

        try:
            tukey = pairwise_tukeyhsd(df_clean[col], df_clean['approach'], alpha=0.05)

            # Extract results using group pair combinations
            from itertools import combinations as _combs
            pairs = list(_combs(range(len(tukey.groupsunique)), 2))
            tukey_df = pd.DataFrame({
                'group1': [tukey.groupsunique[g1] for g1, g2 in pairs],
                'group2': [tukey.groupsunique[g2] for g1, g2 in pairs],
                'meandiff': tukey.meandiffs,
                'p_adj': tukey.pvalues,
                'lower': tukey.confint[:, 0],
                'upper': tukey.confint[:, 1],
                'reject': tukey.reject
            })

            tukey_df['metric'] = metric_info['name']
            tukey_df['metric_id'] = metric_id
            tukey_df['significant'] = tukey_df['reject'].map({True: 'Yes', False: 'No'})
            tukey_df['sig_level'] = tukey_df['p_adj'].apply(
                lambda p: '***' if p < 0.001 else '**' if p < 0.01 else '*' if p < 0.05 else 'ns'
            )

            all_pairwise.append(tukey_df)

        except Exception as e:
            print(f"  Warning: Could not compute Tukey HSD for {metric_id}: {e}")

    if all_pairwise:
        df_pairwise = pd.concat(all_pairwise, ignore_index=True)

        # Reorder columns
        col_order = ['metric', 'metric_id', 'group1', 'group2', 'meandiff', 'p_adj', 'sig_level', 'significant', 'lower', 'upper']
        df_pairwise = df_pairwise[col_order]

        # Save all pairwise
        df_pairwise.to_csv(OUTPUT_DIR / "pairwise_comparisons_all_metrics.csv", index=False)
        print(f"✓ Saved: pairwise_comparisons_all_metrics.csv")

        # Save per-metric files
        for metric_id in df_pairwise['metric_id'].unique():
            metric_data = df_pairwise[df_pairwise['metric_id'] == metric_id]
            metric_data = metric_data.sort_values('p_adj')
            metric_data.to_csv(OUTPUT_DIR / f"pairwise_{metric_id}.csv", index=False)
            print(f"  ✓ Saved: pairwise_{metric_id}.csv")

        # Create summary of significant differences
        sig_only = df_pairwise[df_pairwise['significant'] == 'Yes'].copy()
        sig_only = sig_only.sort_values(['metric_id', 'p_adj'])
        sig_only.to_csv(OUTPUT_DIR / "pairwise_significant_only.csv", index=False)
        print(f"✓ Saved: pairwise_significant_only.csv")

# =============================================================================
# ANOVA SUMMARY TABLE
# =============================================================================

anova_summary = []

for metric_id, metric_info in metrics.items():
    col = metric_info['col']
    if col not in df.columns:
        continue

    df_clean = df.dropna(subset=[col])
    if len(df_clean) == 0:
        continue

    approaches = df_clean['approach'].unique()
    groups = [df_clean[df_clean['approach'] == app][col].values for app in approaches]

    # One-way ANOVA
    f_stat, p_value = stats.f_oneway(*groups)

    # Effect size
    grand_mean = df_clean[col].mean()
    ss_total = ((df_clean[col] - grand_mean) ** 2).sum()
    ss_between = sum(len(g) * (g.mean() - grand_mean) ** 2 for g in groups)
    eta_squared = ss_between / ss_total if ss_total > 0 else 0

    effect = "large" if eta_squared >= 0.14 else "medium" if eta_squared >= 0.06 else "small" if eta_squared >= 0.01 else "negligible"

    anova_summary.append({
        'metric': metric_info['name'],
        'metric_id': metric_id,
        'n_total': len(df_clean),
        'n_groups': len(approaches),
        'df_between': len(approaches) - 1,
        'df_within': len(df_clean) - len(approaches),
        'F_statistic': f_stat,
        'p_value': p_value,
        'eta_squared': eta_squared,
        'effect_size': effect,
        'significant': 'Yes' if p_value < 0.05 else 'No'
    })

df_anova = pd.DataFrame(anova_summary)
df_anova.to_csv(OUTPUT_DIR / "anova_summary_table.csv", index=False)
print(f"✓ Saved: anova_summary_table.csv")

# =============================================================================
# PRINT SUMMARY
# =============================================================================

print("\n" + "="*60)
print("FILES GENERATED IN full_anova_stats/")
print("="*60)
print("""
DESCRIPTIVE STATISTICS:
  - descriptive_statistics_all_metrics.csv  (all metrics combined)
  - descriptive_win_rate.csv
  - descriptive_attempts.csv
  - descriptive_hamming_1.csv
  - descriptive_total_violations.csv
  - descriptive_candidates_after_1.csv
  - descriptive_reduction_rate_1.csv

PAIRWISE COMPARISONS (Tukey HSD):
  - pairwise_comparisons_all_metrics.csv  (all metrics combined)
  - pairwise_significant_only.csv  (only significant comparisons)
  - pairwise_win_rate.csv
  - pairwise_attempts.csv
  - pairwise_hamming_1.csv
  - pairwise_total_violations.csv
  - pairwise_candidates_after_1.csv
  - pairwise_reduction_rate_1.csv

ANOVA SUMMARY:
  - anova_summary_table.csv
""")

print("✓ All files saved successfully!")
