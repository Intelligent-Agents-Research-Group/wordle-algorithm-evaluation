#!/usr/bin/env python3
"""
Repeated Measures ANOVA: Levenshtein Distance Per Round

This script performs repeated measures ANOVA on Levenshtein distance
for each round (1-6), treating target_word as the subject and
approach as the within-subjects factor.

Author: Statistical Analysis Script
Date: January 2026
"""

import pandas as pd
import numpy as np
from scipy import stats
import os
import warnings
from datetime import datetime
warnings.filterwarnings('ignore')

# Try to import pingouin for post-hoc tests
try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False
    print("Note: pingouin not installed, post-hoc tests will be limited")


# Category mappings for aggregation (same as used in other analyses)
CATEGORY_MAPPING = {
    # Algorithms
    'Pure_Algo_css': 'CSS',
    'Pure_Algo_voi': 'VOI',
    'Pure_Algo_random': 'Random',
    'Pure_Algo_pure_random': 'Random',
    'Pure_Algo_css_then_voi': 'CSS_then_VOI',
    'Pure_Algo_voi_then_css': 'VOI_then_CSS',
    'Pure_Algo_css_voi_alternating': 'CSS_VOI_Alt',
    'Pure_Algo_voi_css_alternating': 'VOI_CSS_Alt',
}

# LLM size tiers
SMALL_LLMS = ['llama-3.1-8b', 'mistral-7b', 'granite-8b', 'nemotron-8b', 'gpt-oss-20b']
MID_LLMS = ['codestral-22b', 'gemma-27b']
FRONTIER_LLMS = ['llama-3.1-70b', 'llama-3.3-70b', 'gpt-oss-120b', 'mistral-small']


def categorize_approach(col_name):
    """Map column name to category."""
    # Check algorithm mapping first
    if col_name in CATEGORY_MAPPING:
        return CATEGORY_MAPPING[col_name]

    # Check for Pure LLM
    if col_name.startswith('PureLLM_'):
        for llm in SMALL_LLMS:
            if llm in col_name:
                return 'Small_LLM'
        for llm in MID_LLMS:
            if llm in col_name:
                return 'Mid_LLM'
        for llm in FRONTIER_LLMS:
            if llm in col_name:
                return 'Frontier_LLM'
        return 'LLM_Other'

    # Check for Hybrid
    if col_name.startswith('Hybrid_'):
        return 'Hybrid'

    return None


def load_round_data(round_num, results_dir='results'):
    """Load Levenshtein distance data for a specific round."""
    filepath = os.path.join(results_dir, f'LEVENSHTEIN_DISTANCE_ROUND_{round_num}_BY_GAME_AND_APPROACH.csv')

    if not os.path.exists(filepath):
        print(f"  File not found: {filepath}")
        return None

    df = pd.read_csv(filepath)
    return df


def aggregate_to_categories(df):
    """Aggregate individual approaches to categories."""
    # Get all approach columns (exclude Game_Number)
    approach_cols = [col for col in df.columns if col != 'Game_Number']

    # Create category aggregations
    category_data = {'Game_Number': df['Game_Number']}
    category_values = {}

    for col in approach_cols:
        cat = categorize_approach(col)
        if cat:
            if cat not in category_values:
                category_values[cat] = []
            category_values[cat].append(df[col])

    # Average within each category
    for cat, values in category_values.items():
        if values:
            category_data[cat] = pd.concat(values, axis=1).mean(axis=1)

    return pd.DataFrame(category_data)


def reshape_to_long(df):
    """Reshape wide format to long format for RM-ANOVA."""
    # Melt the dataframe
    long_df = df.melt(
        id_vars=['Game_Number'],
        var_name='approach',
        value_name='levenshtein'
    )
    long_df = long_df.rename(columns={'Game_Number': 'subject'})
    return long_df


def run_rm_anova(long_df, round_num):
    """Run repeated measures ANOVA manually."""
    # Remove rows with NaN
    clean_df = long_df.dropna(subset=['levenshtein']).copy()

    if clean_df.empty:
        return None

    # Get unique subjects and conditions
    subjects = clean_df['subject'].unique()
    conditions = clean_df['approach'].unique()
    n_subjects = len(subjects)
    n_conditions = len(conditions)

    # Need at least 2 subjects and 2 conditions
    if n_subjects < 2 or n_conditions < 2:
        return None

    # Create pivot table - only include complete cases
    try:
        pivot = clean_df.pivot(index='subject', columns='approach', values='levenshtein')
        # Drop rows with any NaN (incomplete cases)
        pivot = pivot.dropna()

        if len(pivot) < 2:
            return None

        n_subjects = len(pivot)
    except Exception as e:
        print(f"  Error creating pivot table: {e}")
        return None

    # Grand mean
    grand_mean = pivot.values.mean()

    # Subject means
    subject_means = pivot.mean(axis=1)

    # Condition means
    condition_means = pivot.mean(axis=0)

    # Total SS
    SS_total = np.sum((pivot.values - grand_mean) ** 2)

    # Between-subjects SS
    SS_subjects = n_conditions * np.sum((subject_means - grand_mean) ** 2)

    # Between-conditions (treatment) SS
    SS_conditions = n_subjects * np.sum((condition_means - grand_mean) ** 2)

    # Error SS (Subject x Condition interaction)
    SS_error = SS_total - SS_subjects - SS_conditions

    # Degrees of freedom
    df_conditions = n_conditions - 1
    df_error = (n_subjects - 1) * (n_conditions - 1)

    # Mean squares
    MS_conditions = SS_conditions / df_conditions
    MS_error = SS_error / df_error if df_error > 0 else 0

    # F-statistic
    F = MS_conditions / MS_error if MS_error > 0 else np.inf

    # p-value
    p_value = 1 - stats.f.cdf(F, df_conditions, df_error) if df_error > 0 else 0

    # Effect size (partial eta-squared)
    eta_sq_partial = SS_conditions / (SS_conditions + SS_error) if (SS_conditions + SS_error) > 0 else 0

    # Omega-squared (less biased)
    omega_sq = (SS_conditions - df_conditions * MS_error) / (SS_total + MS_error) if (SS_total + MS_error) > 0 else 0

    # Descriptive stats by approach
    desc_stats = clean_df.groupby('approach')['levenshtein'].agg(['mean', 'std', 'min', 'max', 'count'])
    desc_stats = desc_stats.sort_values('mean')
    desc_stats['se'] = desc_stats['std'] / np.sqrt(desc_stats['count'])
    desc_stats['95% CI'] = desc_stats['se'] * 1.96

    return {
        'round': round_num,
        'n_subjects': n_subjects,
        'n_conditions': n_conditions,
        'F': F,
        'p': p_value,
        'df_conditions': df_conditions,
        'df_error': df_error,
        'eta_sq_partial': eta_sq_partial,
        'omega_sq': omega_sq,
        'SS_conditions': SS_conditions,
        'SS_error': SS_error,
        'MS_conditions': MS_conditions,
        'MS_error': MS_error,
        'descriptive_stats': desc_stats,
        'condition_means': condition_means.sort_values()
    }


def run_posthoc_tests(long_df):
    """Run post-hoc pairwise comparisons with Bonferroni correction."""
    if not HAS_PINGOUIN:
        return None

    clean_df = long_df.dropna(subset=['levenshtein']).copy()

    if clean_df.empty:
        return None

    try:
        posthoc = pg.pairwise_tests(
            data=clean_df,
            dv='levenshtein',
            within='approach',
            subject='subject',
            padjust='bonf',
            effsize='cohen'
        )
        return posthoc
    except Exception as e:
        print(f"  Post-hoc test error: {e}")
        return None


def generate_report(results, output_dir):
    """Generate detailed report for a round."""
    round_num = results['round']

    report = []
    report.append("=" * 80)
    report.append(f"REPEATED MEASURES ANOVA: LEVENSHTEIN DISTANCE ROUND {round_num}")
    report.append("=" * 80)
    report.append("")
    report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append(f"Metric: Levenshtein Distance (Round {round_num})")
    report.append(f"Description: Edit distance between guess and target word")
    report.append("Lower is better: Yes")
    report.append("")
    report.append("-" * 80)
    report.append("DESIGN")
    report.append("-" * 80)
    report.append(f"Complete cases (subjects): {results['n_subjects']}")
    report.append(f"Conditions (approaches): {results['n_conditions']}")
    report.append("Within-subjects factor: approach")
    report.append("Subject: target_word (game)")
    report.append("")
    report.append("-" * 80)
    report.append("ANOVA TABLE")
    report.append("-" * 80)
    report.append(f"{'Source':<20} {'SS':>12} {'df':>6} {'MS':>14} {'F':>12} {'p':>14}")
    report.append("-" * 80)
    report.append(f"{'Conditions':<20} {results['SS_conditions']:>12.4f} {results['df_conditions']:>6} {results['MS_conditions']:>14.4f} {results['F']:>12.4f} {results['p']:>14.2e}")
    report.append(f"{'Error':<20} {results['SS_error']:>12.4f} {results['df_error']:>6} {results['MS_error']:>14.4f}")
    report.append("")
    report.append("-" * 80)
    report.append("EFFECT SIZES")
    report.append("-" * 80)
    report.append(f"Partial eta-squared (η²p): {results['eta_sq_partial']:.4f}")
    report.append(f"Omega-squared (ω²): {results['omega_sq']:.4f}")
    report.append("")
    report.append("-" * 80)
    report.append("INTERPRETATION")
    report.append("-" * 80)

    # Significance interpretation
    if results['p'] < 0.001:
        sig_text = "HIGHLY SIGNIFICANT (p < 0.001)"
    elif results['p'] < 0.01:
        sig_text = "SIGNIFICANT (p < 0.01)"
    elif results['p'] < 0.05:
        sig_text = "SIGNIFICANT (p < 0.05)"
    else:
        sig_text = "NOT SIGNIFICANT (p >= 0.05)"

    # Effect size interpretation
    eta = results['eta_sq_partial']
    if eta < 0.01:
        effect_text = "negligible"
    elif eta < 0.06:
        effect_text = "small"
    elif eta < 0.14:
        effect_text = "medium"
    else:
        effect_text = "large"

    report.append(f"Result: {sig_text}")
    report.append(f"Effect size: {effect_text} (η²p = {eta:.4f})")
    report.append("")
    report.append(f"F({results['df_conditions']}, {results['df_error']}) = {results['F']:.4f}, p = {results['p']:.2e}, η²p = {results['eta_sq_partial']:.4f}")
    report.append("")
    report.append("-" * 80)
    report.append("DESCRIPTIVE STATISTICS BY APPROACH")
    report.append("-" * 80)
    report.append(results['descriptive_stats'].round(4).to_string())

    return "\n".join(report)


def main():
    """Main analysis function."""
    print("=" * 80)
    print("REPEATED MEASURES ANOVA: LEVENSHTEIN DISTANCE PER ROUND")
    print("=" * 80)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Set up directories
    results_dir = '/Users/kevin/Desktop/wordle/results'
    output_dir = '/Users/kevin/Desktop/wordle/statistical_analysis_results/levenshtein_anova_per_round'
    os.makedirs(output_dir, exist_ok=True)

    # Store results for summary
    all_results = []

    # Process each round
    for round_num in range(1, 7):
        print(f"\n--- Processing Round {round_num} ---")

        # Load data
        df = load_round_data(round_num, results_dir)
        if df is None:
            print(f"  Skipping round {round_num}: no data")
            all_results.append({'round': round_num, 'status': 'no_data'})
            continue

        print(f"  Loaded {len(df)} games, {len(df.columns)-1} approaches")

        # Aggregate to categories
        cat_df = aggregate_to_categories(df)
        print(f"  Aggregated to {len(cat_df.columns)-1} categories: {list(cat_df.columns[1:])}")

        # Reshape to long format
        long_df = reshape_to_long(cat_df)
        print(f"  Long format: {len(long_df)} observations")

        # Run RM-ANOVA
        results = run_rm_anova(long_df, round_num)

        if results is None:
            print(f"  Skipping round {round_num}: insufficient data for ANOVA")
            all_results.append({'round': round_num, 'status': 'insufficient_data'})
            continue

        print(f"  N={results['n_subjects']}, F={results['F']:.4f}, p={results['p']:.2e}, η²p={results['eta_sq_partial']:.4f}")

        # Run post-hoc tests
        posthoc = run_posthoc_tests(long_df)
        if posthoc is not None:
            sig_count = len(posthoc[posthoc['p-corr'] < 0.05])
            print(f"  Post-hoc: {sig_count} significant pairwise comparisons")
            results['posthoc'] = posthoc

        all_results.append(results)

        # Generate and save report
        report = generate_report(results, output_dir)
        report_file = os.path.join(output_dir, f'rm_anova_levenshtein_{round_num}_report.txt')
        with open(report_file, 'w') as f:
            f.write(report)

            # Add post-hoc results if available
            if posthoc is not None:
                f.write("\n\n")
                f.write("-" * 80 + "\n")
                f.write("POST-HOC PAIRWISE COMPARISONS (Bonferroni-corrected)\n")
                f.write("-" * 80 + "\n")
                sig_posthoc = posthoc[posthoc['p-corr'] < 0.05]
                f.write(f"Significant comparisons: {len(sig_posthoc)} out of {len(posthoc)}\n\n")
                cols = ['A', 'B', 'T', 'p-unc', 'p-corr', 'cohen']
                if len(sig_posthoc) > 0:
                    f.write("Significant Pairwise Differences (p-corr < 0.05):\n")
                    f.write(sig_posthoc[cols].to_string(index=False))
                f.write("\n\nAll Pairwise Comparisons (sorted by p-value):\n")
                f.write(posthoc.sort_values('p-unc')[cols].to_string(index=False))

        print(f"  Saved: {report_file}")

        # Save descriptive stats
        desc_file = os.path.join(output_dir, f'rm_anova_levenshtein_{round_num}_descriptive_stats.csv')
        results['descriptive_stats'].to_csv(desc_file)

        # Save post-hoc if available
        if posthoc is not None:
            posthoc_file = os.path.join(output_dir, f'rm_anova_levenshtein_{round_num}_posthoc_pairwise.csv')
            posthoc.to_csv(posthoc_file, index=False)

    # Generate summary across all rounds
    print("\n" + "=" * 80)
    print("SUMMARY ACROSS ALL ROUNDS")
    print("=" * 80)

    summary_lines = []
    summary_lines.append("=" * 80)
    summary_lines.append("REPEATED MEASURES ANOVA: LEVENSHTEIN DISTANCE PER ROUND - SUMMARY")
    summary_lines.append("=" * 80)
    summary_lines.append("")
    summary_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    summary_lines.append("Analysis: Repeated Measures ANOVA for Levenshtein Distance")
    summary_lines.append("Rounds analyzed: 1-6")
    summary_lines.append("Within-subjects factor: Approach")
    summary_lines.append("Subject: Target word")
    summary_lines.append("")
    summary_lines.append("-" * 80)
    summary_lines.append("SUMMARY OF RESULTS BY ROUND")
    summary_lines.append("-" * 80)
    summary_lines.append("")
    summary_lines.append(f"{'Round':<8} {'N':>8} {'F':>12} {'p-value':>14} {'η²p':>10} {'Effect':>12} {'Sig?':>8}")
    summary_lines.append("-" * 80)

    summary_data = []

    for r in all_results:
        if 'status' in r:
            summary_lines.append(f"{r['round']:<8} {'N/A':>8} {'N/A':>12} {'N/A':>14} {'N/A':>10} {'N/A':>12} {'N/A':>8}")
            summary_data.append({
                'Round': r['round'], 'N': None, 'F': None, 'p_value': None,
                'eta_sq_partial': None, 'effect_size': None, 'significant': None
            })
        else:
            # Significance symbol
            if r['p'] < 0.001:
                sig = "***"
            elif r['p'] < 0.01:
                sig = "**"
            elif r['p'] < 0.05:
                sig = "*"
            else:
                sig = "ns"

            # Effect size
            eta = r['eta_sq_partial']
            if eta < 0.01:
                effect = "negligible"
            elif eta < 0.06:
                effect = "small"
            elif eta < 0.14:
                effect = "medium"
            else:
                effect = "large"

            summary_lines.append(f"{r['round']:<8} {r['n_subjects']:>8} {r['F']:>12.4f} {r['p']:>14.2e} {eta:>10.4f} {effect:>12} {sig:>8}")
            summary_data.append({
                'Round': r['round'], 'N': r['n_subjects'], 'F': r['F'],
                'p_value': r['p'], 'eta_sq_partial': eta, 'effect_size': effect,
                'significant': sig
            })

    summary_lines.append("")
    summary_lines.append("Significance: *** p<0.001, ** p<0.01, * p<0.05, ns = not significant")
    summary_lines.append("Effect size (η²p): <0.01 negligible, 0.01-0.06 small, 0.06-0.14 medium, >0.14 large")
    summary_lines.append("")
    summary_lines.append("-" * 80)
    summary_lines.append("INTERPRETATION")
    summary_lines.append("-" * 80)
    summary_lines.append("")
    summary_lines.append("Round 1: First guess (no feedback yet) - all approaches start similarly")
    summary_lines.append("Round 2-3: Key differentiation rounds - approaches use feedback differently")
    summary_lines.append("Round 4-6: Later rounds have fewer observations (games that haven't ended)")
    summary_lines.append("")
    summary_lines.append("Lower Levenshtein distance = closer to target = better convergence")
    summary_lines.append("")
    summary_lines.append("-" * 80)
    summary_lines.append("BEST PERFORMERS BY ROUND (Lowest Mean Levenshtein Distance)")
    summary_lines.append("-" * 80)
    summary_lines.append("")

    for r in all_results:
        if 'condition_means' in r:
            best = r['condition_means'].index[0]
            best_val = r['condition_means'].iloc[0]
            summary_lines.append(f"Round {r['round']}: {best} (mean = {best_val:.3f})")

    summary_lines.append("")
    summary_lines.append("=" * 80)
    summary_lines.append("FILES GENERATED")
    summary_lines.append("=" * 80)
    summary_lines.append("")

    for r in all_results:
        if 'status' not in r:
            summary_lines.append(f"• rm_anova_levenshtein_{r['round']}_descriptive_stats.csv")
            summary_lines.append(f"• rm_anova_levenshtein_{r['round']}_posthoc_pairwise.csv")
            summary_lines.append(f"• rm_anova_levenshtein_{r['round']}_report.txt")

    summary_lines.append("")
    summary_lines.append("=" * 80)
    summary_lines.append("END OF SUMMARY")
    summary_lines.append("=" * 80)

    # Print and save summary
    summary_text = "\n".join(summary_lines)
    print(summary_text)

    summary_file = os.path.join(output_dir, 'summary_all_rounds.txt')
    with open(summary_file, 'w') as f:
        f.write(summary_text)

    # Save summary CSV
    summary_df = pd.DataFrame(summary_data)
    summary_csv = os.path.join(output_dir, 'summary_all_rounds.csv')
    summary_df.to_csv(summary_csv, index=False)

    print(f"\n✓ Summary saved to: {summary_file}")
    print(f"✓ Summary CSV saved to: {summary_csv}")
    print(f"\n✓ All results saved to: {output_dir}/")


if __name__ == "__main__":
    main()
