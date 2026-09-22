#!/usr/bin/env python3
"""
Create Repeated Measures ANOVA files with True CSS (replacing old CSS)
Matches the format of old_rm_total directory
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

try:
    import pingouin as pg
    HAS_PINGOUIN = True
except ImportError:
    HAS_PINGOUIN = False
    print("pingouin not available - install with: pip install pingouin")

BASE_DIR = Path("/Users/kevin/Desktop/wordle")
OUTPUT_DIR = BASE_DIR / "statistical_analysis_results" / "full_anova_stats"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# DATA LOADING FUNCTIONS
# =============================================================================

def load_true_css_per_game():
    """Load True CSS per-game data from results file."""
    violations_file = BASE_DIR / "results" / "algorithms" / "true_css" / "css_true_results_with_violations.csv"
    candidates_file = BASE_DIR / "results" / "algorithms" / "true_css" / "css_true_results_with_candidates.csv"

    df = pd.read_csv(violations_file)

    # Also load candidates data if available
    if candidates_file.exists():
        df_cand = pd.read_csv(candidates_file)
        # Merge candidates columns
        cand_cols = [c for c in df_cand.columns if 'candidates' in c.lower() or 'reduction' in c.lower()]
        if cand_cols:
            df = df.merge(df_cand[['game_number'] + cand_cols], on='game_number', how='left')

    return df

def load_algorithm_data():
    """Load algorithm data (VOI and algorithm combinations)."""
    raw_file = BASE_DIR / "results" / "algorithms" / "raw data" / "algorithm_results_20251211_175156.csv"

    if not raw_file.exists():
        # Try alternative locations
        for alt_file in BASE_DIR.glob("results/algorithms/**/*.csv"):
            if 'algorithm_results' in str(alt_file) and 'true_css' not in str(alt_file):
                raw_file = alt_file
                break

    if raw_file.exists():
        df = pd.read_csv(raw_file)
        return df
    return None

def load_per_game_matrix(metric_name):
    """Load per-game matrix data for a metric."""
    file_map = {
        'total_violations': 'TOTAL_VIOLATIONS_BY_GAME_AND_APPROACH.csv',
        'attempts': 'ATTEMPTS_BY_GAME_AND_APPROACH.csv',
        'hamming_1': 'HAMMING_DISTANCE_BY_GAME_AND_APPROACH.csv',
        'convergence_1': 'CONVERGENCE_RATE_BY_GAME_AND_APPROACH.csv',
    }

    filename = file_map.get(metric_name)
    if not filename:
        return None

    filepath = BASE_DIR / "data" / "per_game_stats_true_css" / filename
    if filepath.exists():
        return pd.read_csv(filepath)
    return None

def get_target_words():
    """Get list of target words used in experiments."""
    # Try to get from True CSS data
    true_css = load_true_css_per_game()
    if true_css is not None and 'target_word' in true_css.columns:
        return true_css['target_word'].tolist()

    # Fallback: generate generic word IDs
    return [f"word_{i}" for i in range(1, 101)]

# =============================================================================
# APPROACH MAPPING
# =============================================================================

# Map from data column names to display names (matching old_rm_total)
APPROACH_MAP = {
    'CSS': 'CSS',  # New True CSS replaces old CSS
    'Pure_Algo_css': 'CSS_OLD',  # Mark old CSS as OLD
    'Pure_Algo_voi': 'VOI',
    'Pure_Algo_css_then_voi': 'CSS_then_VOI',
    'Pure_Algo_voi_then_css': 'VOI_then_CSS',
    'Pure_Algo_css_voi_alternating': 'CSS_VOI_Alt',
    'Pure_Algo_voi_css_alternating': 'VOI_CSS_Alt',
    'Pure_Algo_random': 'Random',
    'Pure_Algo_pure_random': 'Pure_Random',
}

# LLM tier mapping (best performer from each tier)
LLM_TIERS = {
    'Frontier_LLM': 'PureLLM_llama-3.3-70b_CoT',  # Best frontier
    'Mid_LLM': 'PureLLM_gemma-27b_ZeroShot',  # Best mid-tier
    'Small_LLM': 'PureLLM_mistral-7b_ZeroShot',  # Best small
}

# Best hybrid
BEST_HYBRID = 'Hybrid_gemma-27b_CSS_ZeroShot'

def get_approach_order():
    """Return the standard approach order."""
    return [
        'CSS',
        'VOI',
        'Frontier_LLM',
        'Mid_LLM',
        'Small_LLM',
        'Hybrid',
        'Random',
        'Pure_Random',
    ]

# =============================================================================
# DATA PREPARATION
# =============================================================================

def prepare_rm_data(metric_name):
    """
    Prepare data for repeated measures ANOVA.
    Returns DataFrame in long format with columns: subject, approach, value
    Uses the combined_data.csv which has clean data.
    """
    # Load combined data
    combined_file = OUTPUT_DIR / "combined_data.csv"
    if not combined_file.exists():
        print(f"  Combined data file not found: {combined_file}")
        return None, []

    df_combined = pd.read_csv(combined_file)

    # Get target words
    target_words = get_target_words()

    # Map metric names to column names
    col_map = {
        'total_violations': 'total_violations',
        'attempts': 'attempts',
        'hamming_1': 'hamming_1',
        'hamming_2': 'hamming_2',
        'hamming_3': 'hamming_3',
        'hamming_4': 'hamming_4',
        'hamming_5': 'hamming_5',
        'hamming_6': 'hamming_6',
        'win_rate': 'win_rate',
        'candidates_after_1': 'candidates_after_1',
        'reduction_rate_1': 'reduction_rate_1',
        'convergence_rate': 'convergence_rate',
    }

    if metric_name not in col_map or col_map[metric_name] not in df_combined.columns:
        print(f"  Metric {metric_name} not found in combined data")
        return None, []

    value_col = col_map[metric_name]

    # Map current approach names to old_rm_total format
    approach_name_map = {
        'CSS': 'CSS',
        'VOI': 'VOI',
        'Random': 'CSS_then_VOI',  # Note: We don't have the algorithm combinations in combined_data
        'Pure_Random': 'Random',  # This is the pure random baseline
        'Small_LLM': 'Small_LLM',
        'Mid_LLM': 'Mid_LLM',
        'Frontier_LLM': 'Frontier_LLM',
        'Hybrid': 'Hybrid',
    }

    # Add game_number as subject if not present
    if 'game_number' not in df_combined.columns:
        df_combined['game_number'] = df_combined.groupby('approach').cumcount() + 1

    # Use game_number as subject (ensures consistency across approaches)
    df_combined['subject'] = df_combined['game_number'].apply(lambda x: f"game_{x}")

    # Rename value column to 'value'
    df = df_combined[['subject', 'approach', value_col]].copy()
    df = df.rename(columns={value_col: 'value'})

    # Convert to numeric
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    df = df.dropna(subset=['value'])

    # Get available approaches
    available_approaches = df['approach'].unique().tolist()

    # Keep only subjects with all approaches
    n_approaches = df['approach'].nunique()
    subject_counts = df.groupby('subject')['approach'].nunique()
    complete_subjects = subject_counts[subject_counts == n_approaches].index
    df = df[df['subject'].isin(complete_subjects)]

    return df, available_approaches

# =============================================================================
# REPEATED MEASURES ANOVA
# =============================================================================

def run_rm_anova(df, metric_name, metric_display_name, lower_is_better=True):
    """
    Run repeated measures ANOVA and generate output files.
    """
    if not HAS_PINGOUIN:
        print("pingouin required for repeated measures ANOVA")
        return

    # Get unique approaches in order
    approach_order = get_approach_order()
    available = df['approach'].unique()
    approaches = [a for a in approach_order if a in available]

    n_subjects = df['subject'].nunique()
    n_conditions = len(approaches)

    # Run RM ANOVA
    aov = pg.rm_anova(data=df, dv='value', within='approach', subject='subject', detailed=True)

    # Extract ANOVA statistics
    ss_cond = aov.loc[0, 'SS']
    df_cond = int(aov.loc[0, 'DF'])
    ms_cond = aov.loc[0, 'MS']
    f_stat = aov.loc[0, 'F']
    p_value = aov.loc[0, 'p-unc']

    # Error terms (from residual)
    ss_error = aov.loc[1, 'SS'] if len(aov) > 1 else 0
    df_error = int(aov.loc[1, 'DF']) if len(aov) > 1 else (n_subjects - 1) * (n_conditions - 1)
    ms_error = ss_error / df_error if df_error > 0 else 0

    # Effect sizes
    eta_sq_p = aov.loc[0, 'np2'] if 'np2' in aov.columns else ss_cond / (ss_cond + ss_error)

    # Omega squared
    omega_sq = (ss_cond - df_cond * ms_error) / (ss_cond + ss_error + ms_error) if (ss_cond + ss_error + ms_error) > 0 else 0

    # Descriptive statistics by approach
    desc_stats = df.groupby('approach')['value'].agg(['mean', 'std', 'min', 'max', 'count'])
    desc_stats['se'] = desc_stats['std'] / np.sqrt(desc_stats['count'])
    desc_stats['95% CI'] = desc_stats['se'] * 1.96
    desc_stats = desc_stats.reindex(approaches)

    # Post-hoc pairwise comparisons
    posthoc = pg.pairwise_tests(data=df, dv='value', within='approach', subject='subject',
                                 parametric=True, padjust='bonf')

    # ==========================================================================
    # Generate report file (matching old_rm_total format)
    # ==========================================================================

    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append(f"REPEATED MEASURES ANOVA: {metric_name.upper()}")
    report_lines.append("=" * 80)
    report_lines.append("")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Metric: {metric_name}")
    report_lines.append(f"Description: {metric_display_name}")
    report_lines.append(f"Lower is better: {'Yes' if lower_is_better else 'No'}")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("DESIGN")
    report_lines.append("-" * 80)
    report_lines.append(f"Complete cases (subjects): {n_subjects}")
    report_lines.append(f"Conditions (approaches): {n_conditions}")
    report_lines.append("Within-subjects factor: approach")
    report_lines.append("Subject: target_word")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("ANOVA TABLE")
    report_lines.append("-" * 80)
    report_lines.append(f"{'Source':<20} {'SS':>12} {'df':>6} {'MS':>12} {'F':>12} {'p':>12}")
    report_lines.append("-" * 70)
    report_lines.append(f"{'Conditions':<20} {ss_cond:>12.4f} {df_cond:>6} {ms_cond:>12.4f} {f_stat:>12.4f} {p_value:>12.2e}")
    report_lines.append(f"{'Error':<20} {ss_error:>12.4f} {df_error:>6} {ms_error:>12.4f}")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("EFFECT SIZES")
    report_lines.append("-" * 80)
    report_lines.append(f"Partial eta-squared (eta^2p): {eta_sq_p:.4f}")
    report_lines.append(f"Omega-squared (omega^2): {omega_sq:.4f}")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("INTERPRETATION")
    report_lines.append("-" * 80)

    if p_value < 0.001:
        sig_level = "HIGHLY SIGNIFICANT (p < 0.001)"
    elif p_value < 0.01:
        sig_level = "SIGNIFICANT (p < 0.01)"
    elif p_value < 0.05:
        sig_level = "SIGNIFICANT (p < 0.05)"
    else:
        sig_level = "NOT SIGNIFICANT (p >= 0.05)"

    effect_size_label = "large" if eta_sq_p >= 0.14 else "medium" if eta_sq_p >= 0.06 else "small"

    report_lines.append(f"Result: {sig_level}")
    report_lines.append(f"Effect size: {effect_size_label} (eta^2p = {eta_sq_p:.4f})")
    report_lines.append("")
    report_lines.append(f"F({df_cond}, {df_error}) = {f_stat:.4f}, p = {p_value:.2e}, eta^2p = {eta_sq_p:.4f}")
    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("DESCRIPTIVE STATISTICS BY APPROACH")
    report_lines.append("-" * 80)

    # Format descriptive stats table
    header = f"{'approach':>12} {'mean':>10} {'std':>10} {'min':>5} {'max':>10} {'count':>6} {'se':>10} {'95% CI':>10}"
    report_lines.append(header)

    for approach in approaches:
        if approach in desc_stats.index:
            row = desc_stats.loc[approach]
            line = f"{approach:>12} {row['mean']:>10.6f} {row['std']:>10.6f} {row['min']:>5.1f} {row['max']:>10.6f} {int(row['count']):>6} {row['se']:>10.6f} {row['95% CI']:>10.6f}"
            report_lines.append(line)

    report_lines.append("")
    report_lines.append("-" * 80)
    report_lines.append("POST-HOC PAIRWISE COMPARISONS (Bonferroni-corrected)")
    report_lines.append("-" * 80)

    # Count significant comparisons
    sig_count = (posthoc['p-corr'] < 0.05).sum() if 'p-corr' in posthoc.columns else 0
    total_comparisons = len(posthoc)
    report_lines.append(f"Significant comparisons: {sig_count} out of {total_comparisons}")
    report_lines.append("")

    # Significant pairwise differences
    report_lines.append("Significant Pairwise Differences (p-corr < 0.05):")
    report_lines.append(f"{'A':>12} {'B':>12} {'T':>10} {'p-unc':>12} {'p-corr':>12} {'cohen':>8}")

    sig_pairs = posthoc[posthoc['p-corr'] < 0.05] if 'p-corr' in posthoc.columns else posthoc[posthoc['p-unc'] < 0.05]
    for _, row in sig_pairs.iterrows():
        a = row['A']
        b = row['B']
        t = row['T'] if pd.notna(row['T']) else float('nan')
        p_unc = row['p-unc'] if pd.notna(row['p-unc']) else float('nan')
        p_corr = row['p-corr'] if 'p-corr' in row and pd.notna(row['p-corr']) else float('nan')
        cohen = row['cohen'] if 'cohen' in row and pd.notna(row['cohen']) else float('nan')

        line = f"{a:>12} {b:>12} {t:>10.6f} {p_unc:>12.2e} {p_corr:>12.2e} {cohen:>8.6f}"
        report_lines.append(line)

    report_lines.append("")
    report_lines.append("All Pairwise Comparisons (sorted by p-value):")
    report_lines.append(f"{'A':>12} {'B':>12} {'T':>10} {'dof':>6} {'p-unc':>12} {'p-corr':>12} {'cohen':>8}")

    posthoc_sorted = posthoc.sort_values('p-unc')
    for _, row in posthoc_sorted.iterrows():
        a = row['A']
        b = row['B']
        t = row['T'] if pd.notna(row['T']) else float('nan')
        dof = row['dof'] if 'dof' in row and pd.notna(row['dof']) else 99.0
        p_unc = row['p-unc'] if pd.notna(row['p-unc']) else float('nan')
        p_corr = row['p-corr'] if 'p-corr' in row and pd.notna(row['p-corr']) else float('nan')
        cohen = row['cohen'] if 'cohen' in row and pd.notna(row['cohen']) else float('nan')

        if pd.isna(t):
            line = f"{a:>12} {b:>12} {'NaN':>10} {dof:>6.1f} {'NaN':>12} {'NaN':>12} {'NaN':>8}"
        else:
            line = f"{a:>12} {b:>12} {t:>10.6f} {dof:>6.1f} {p_unc:>12.2e} {p_corr:>12.2e} {cohen:>8.6f}"
        report_lines.append(line)

    report_lines.append("")
    report_lines.append("=" * 80)
    report_lines.append("END OF REPORT")
    report_lines.append("=" * 80)
    report_lines.append("")

    # Save report
    report_file = OUTPUT_DIR / f"rm_anova_{metric_name}_report.txt"
    with open(report_file, 'w') as f:
        f.write('\n'.join(report_lines))
    print(f"  Saved: {report_file.name}")

    # ==========================================================================
    # Save descriptive stats CSV
    # ==========================================================================
    desc_csv = desc_stats.reset_index()
    desc_csv.columns = ['approach', 'mean', 'std', 'min', 'max', 'count', 'se', '95% CI']
    desc_csv.to_csv(OUTPUT_DIR / f"rm_anova_{metric_name}_descriptive_stats.csv", index=False)
    print(f"  Saved: rm_anova_{metric_name}_descriptive_stats.csv")

    # ==========================================================================
    # Save posthoc pairwise CSV (pingouin format)
    # ==========================================================================
    posthoc.to_csv(OUTPUT_DIR / f"rm_anova_{metric_name}_posthoc_pairwise.csv", index=False)
    print(f"  Saved: rm_anova_{metric_name}_posthoc_pairwise.csv")

    return {
        'metric': metric_name,
        'F': f_stat,
        'p': p_value,
        'eta_sq_p': eta_sq_p,
        'omega_sq': omega_sq,
        'n_subjects': n_subjects,
        'n_conditions': n_conditions
    }

# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("REPEATED MEASURES ANOVA WITH TRUE CSS")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    print("")

    metrics = [
        ('win_rate', 'Win rate (proportion of games solved)', False),
        ('total_violations', 'Sum of all constraint violations across all rounds', True),
        ('attempts', 'Number of attempts to solve', True),
        ('hamming_1', 'Hamming distance after round 1', True),
        ('hamming_2', 'Hamming distance after round 2', True),
        ('hamming_3', 'Hamming distance after round 3', True),
        ('hamming_4', 'Hamming distance after round 4', True),
        ('hamming_5', 'Hamming distance after round 5', True),
        ('hamming_6', 'Hamming distance after round 6', True),
        ('candidates_after_1', 'Remaining candidates after round 1 (search space)', True),
        ('reduction_rate_1', 'Search space reduction rate after round 1', False),
        ('convergence_rate', 'Convergence rate (Hamming decrease per round)', False),
    ]

    results = []

    for metric_name, description, lower_is_better in metrics:
        print(f"\nProcessing: {metric_name}")
        print("-" * 40)

        try:
            df, valid_approaches = prepare_rm_data(metric_name)

            if df is None or len(df) == 0:
                print(f"  No data available for {metric_name}")
                continue

            print(f"  Data shape: {len(df)} observations")
            print(f"  Subjects: {df['subject'].nunique()}")
            print(f"  Approaches: {', '.join(valid_approaches)}")

            result = run_rm_anova(df, metric_name, description, lower_is_better)
            if result:
                results.append(result)

        except Exception as e:
            print(f"  Error: {e}")
            import traceback
            traceback.print_exc()

    # Summary table
    if results:
        print("\n" + "=" * 60)
        print("SUMMARY OF ALL RM-ANOVA RESULTS")
        print("=" * 60)

        summary_df = pd.DataFrame(results)
        summary_df.to_csv(OUTPUT_DIR / "rm_anova_summary.csv", index=False)
        print(f"\nSaved: rm_anova_summary.csv")

        print("\n" + summary_df.to_string(index=False))

    print("\n" + "=" * 60)
    print("COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
