#!/usr/bin/env python3
"""
Update data files with True CSS (minimax regret) replacing old CSS (entropy-based).
Then run ANOVA and Repeated Measures ANOVA on the updated data.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats
import pingouin as pg
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# Paths
BASE_DIR = Path("/Users/kevin/Desktop/wordle")
DATA_DIR = BASE_DIR / "data" / "per_game_stats"
TRUE_CSS_FILE = BASE_DIR / "results/algorithms/true_css/css_true_results_with_candidates.csv"
OUTPUT_DIR = BASE_DIR / "statistical_analysis_results"
OUTPUT_DIR.mkdir(exist_ok=True)

print("="*80)
print("UPDATE DATA WITH TRUE CSS AND RUN STATISTICAL ANALYSES")
print("="*80)
print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# ============================================================================
# STEP 1: Load True CSS data
# ============================================================================
print("STEP 1: Loading True CSS data...")
print("-"*80)

true_css = pd.read_csv(TRUE_CSS_FILE)
print(f"Loaded True CSS data: {len(true_css)} games")
print(f"Win rate: {true_css['won'].mean()*100:.1f}%")
print(f"Average attempts (wins): {true_css[true_css['won']==True]['attempts'].mean():.2f}")
print()

# ============================================================================
# STEP 2: Update ATTEMPTS_BY_GAME_AND_APPROACH.csv
# ============================================================================
print("STEP 2: Updating ATTEMPTS_BY_GAME_AND_APPROACH.csv...")
print("-"*80)

attempts_file = DATA_DIR / "ATTEMPTS_BY_GAME_AND_APPROACH.csv"
df_attempts = pd.read_csv(attempts_file)

# Replace Pure_Algo_css column with True CSS attempts
if 'Pure_Algo_css' in df_attempts.columns:
    old_values = df_attempts['Pure_Algo_css'].copy()

    # Map True CSS attempts (use 'Loss' for losses)
    new_values = []
    for i, row in true_css.iterrows():
        if row['won']:
            new_values.append(int(row['attempts']))
        else:
            new_values.append('Loss')

    df_attempts['Pure_Algo_css'] = new_values
    print(f"Updated Pure_Algo_css column")
    print(f"  Old wins: {(old_values != 'Loss').sum()}")
    print(f"  New wins: {(df_attempts['Pure_Algo_css'] != 'Loss').sum()}")

# Save updated file
df_attempts.to_csv(attempts_file, index=False)
print(f"Saved: {attempts_file}")
print()

# ============================================================================
# STEP 3: Update HAMMING_DISTANCE_BY_GAME_AND_APPROACH.csv
# ============================================================================
print("STEP 3: Updating HAMMING_DISTANCE_BY_GAME_AND_APPROACH.csv...")
print("-"*80)

hamming_file = DATA_DIR / "HAMMING_DISTANCE_BY_GAME_AND_APPROACH.csv"
df_hamming = pd.read_csv(hamming_file)

# Calculate average hamming distance per game for True CSS
if 'Pure_Algo_css' in df_hamming.columns:
    new_hamming = []
    for i, row in true_css.iterrows():
        hamming_vals = []
        for r in range(1, 7):
            col = f'hamming_{r}'
            if col in row and pd.notna(row[col]):
                hamming_vals.append(row[col])
        new_hamming.append(np.mean(hamming_vals) if hamming_vals else np.nan)

    df_hamming['Pure_Algo_css'] = new_hamming
    print(f"Updated Pure_Algo_css column with average Hamming distance per game")

df_hamming.to_csv(hamming_file, index=False)
print(f"Saved: {hamming_file}")
print()

# ============================================================================
# STEP 4: Update LEVENSHTEIN_DISTANCE_BY_GAME_AND_APPROACH.csv
# ============================================================================
print("STEP 4: Updating LEVENSHTEIN_DISTANCE_BY_GAME_AND_APPROACH.csv...")
print("-"*80)

levenshtein_file = DATA_DIR / "LEVENSHTEIN_DISTANCE_BY_GAME_AND_APPROACH.csv"
df_levenshtein = pd.read_csv(levenshtein_file)

if 'Pure_Algo_css' in df_levenshtein.columns:
    new_levenshtein = []
    for i, row in true_css.iterrows():
        lev_vals = []
        for r in range(1, 7):
            col = f'levenshtein_{r}'
            if col in row and pd.notna(row[col]):
                lev_vals.append(row[col])
        new_levenshtein.append(np.mean(lev_vals) if lev_vals else np.nan)

    df_levenshtein['Pure_Algo_css'] = new_levenshtein
    print(f"Updated Pure_Algo_css column with average Levenshtein distance per game")

df_levenshtein.to_csv(levenshtein_file, index=False)
print(f"Saved: {levenshtein_file}")
print()

# ============================================================================
# STEP 5: Update TOTAL_VIOLATIONS_BY_GAME_AND_APPROACH.csv
# ============================================================================
print("STEP 5: Updating TOTAL_VIOLATIONS_BY_GAME_AND_APPROACH.csv...")
print("-"*80)

violations_file = DATA_DIR / "TOTAL_VIOLATIONS_BY_GAME_AND_APPROACH.csv"
df_violations = pd.read_csv(violations_file)

if 'Pure_Algo_css' in df_violations.columns:
    # True CSS has 0 violations by design (algorithms always respect constraints)
    df_violations['Pure_Algo_css'] = 0
    print(f"Updated Pure_Algo_css column (all zeros - algorithms have no violations)")

df_violations.to_csv(violations_file, index=False)
print(f"Saved: {violations_file}")
print()

# ============================================================================
# STEP 6: Update CONVERGENCE_RATE_BY_GAME_AND_APPROACH.csv
# ============================================================================
print("STEP 6: Updating CONVERGENCE_RATE_BY_GAME_AND_APPROACH.csv...")
print("-"*80)

convergence_file = DATA_DIR / "CONVERGENCE_RATE_BY_GAME_AND_APPROACH.csv"
df_convergence = pd.read_csv(convergence_file)

if 'Pure_Algo_css' in df_convergence.columns:
    new_conv = []
    for i, row in true_css.iterrows():
        h1 = row.get('hamming_1', np.nan)
        h6 = row.get('hamming_6', np.nan)
        if pd.notna(h1):
            # Find last non-nan hamming
            last_h = h1
            for r in range(2, 7):
                col = f'hamming_{r}'
                if col in row and pd.notna(row[col]):
                    last_h = row[col]
            # Convergence rate = (h1 - last_h) / (attempts - 1)
            attempts = row['attempts'] if row['won'] else 6
            if attempts > 1:
                conv_rate = (h1 - last_h) / (attempts - 1)
            else:
                conv_rate = 0
            new_conv.append(conv_rate)
        else:
            new_conv.append(np.nan)

    df_convergence['Pure_Algo_css'] = new_conv
    print(f"Updated Pure_Algo_css column with convergence rate per game")

df_convergence.to_csv(convergence_file, index=False)
print(f"Saved: {convergence_file}")
print()

# ============================================================================
# STEP 7: Update ALL_APPROACHES_FULL_METRICS.csv
# ============================================================================
print("STEP 7: Updating ALL_APPROACHES_FULL_METRICS.csv...")
print("-"*80)

full_metrics_file = DATA_DIR / "ALL_APPROACHES_FULL_METRICS.csv"
df_full = pd.read_csv(full_metrics_file)

# Find and update the Pure_Algo_css row
css_idx = df_full[df_full['Approach'] == 'Pure_Algo_css'].index
if len(css_idx) > 0:
    idx = css_idx[0]

    # Calculate metrics from True CSS
    wins = true_css['won'].sum()
    losses = len(true_css) - wins
    win_rate = wins / len(true_css) * 100

    winning_games = true_css[true_css['won'] == True]
    avg_attempts = winning_games['attempts'].mean() if len(winning_games) > 0 else np.nan
    min_attempts = winning_games['attempts'].min() if len(winning_games) > 0 else np.nan
    max_attempts = winning_games['attempts'].max() if len(winning_games) > 0 else np.nan

    # Count attempts distribution
    count_2 = (winning_games['attempts'] == 2).sum()
    count_3 = (winning_games['attempts'] == 3).sum()
    count_4 = (winning_games['attempts'] == 4).sum()
    count_5 = (winning_games['attempts'] == 5).sum()
    count_6 = (winning_games['attempts'] == 6).sum()

    # Hamming and Levenshtein by attempt
    hamming_by_attempt = []
    lev_by_attempt = []
    for r in range(1, 7):
        h_col = f'hamming_{r}'
        l_col = f'levenshtein_{r}'
        hamming_by_attempt.append(true_css[h_col].mean() if h_col in true_css.columns else np.nan)
        lev_by_attempt.append(true_css[l_col].mean() if l_col in true_css.columns else np.nan)

    # Update the row
    df_full.loc[idx, 'Total_Games'] = len(true_css)
    df_full.loc[idx, 'Wins'] = wins
    df_full.loc[idx, 'Losses'] = losses
    df_full.loc[idx, 'Win_Rate_%'] = win_rate
    df_full.loc[idx, 'Avg_Attempts'] = avg_attempts
    df_full.loc[idx, 'Min_Attempts'] = min_attempts
    df_full.loc[idx, 'Max_Attempts'] = max_attempts
    df_full.loc[idx, 'Count_2_Attempts'] = count_2
    df_full.loc[idx, 'Count_3_Attempts'] = count_3
    df_full.loc[idx, 'Count_4_Attempts'] = count_4
    df_full.loc[idx, 'Count_5_Attempts'] = count_5
    df_full.loc[idx, 'Count_6_Attempts'] = count_6

    for i, (h, l) in enumerate(zip(hamming_by_attempt, lev_by_attempt), 1):
        df_full.loc[idx, f'Hamming_Attempt_{i}'] = h
        df_full.loc[idx, f'Levenshtein_Attempt_{i}'] = l

    print(f"Updated Pure_Algo_css row:")
    print(f"  Win Rate: {win_rate:.1f}%")
    print(f"  Avg Attempts: {avg_attempts:.2f}")

df_full.to_csv(full_metrics_file, index=False)
print(f"Saved: {full_metrics_file}")
print()

# ============================================================================
# STEP 8: Run ANOVA on Attempts
# ============================================================================
print("STEP 8: Running ANOVA on Attempts...")
print("-"*80)

# Prepare data for ANOVA - comparing main categories
# Categories: CSS, VOI, Random, Small_LLM, Mid_LLM, Frontier_LLM, Hybrid

# Load updated attempts data
df_attempts = pd.read_csv(attempts_file)

# Convert 'Loss' to NaN for numeric analysis
for col in df_attempts.columns:
    if col != 'Game_Number':
        df_attempts[col] = pd.to_numeric(df_attempts[col], errors='coerce')

# Define category mappings
categories = {
    'CSS': ['Pure_Algo_css'],
    'VOI': ['Pure_Algo_voi'],
    'Random': ['Pure_Algo_random'],
    'Hybrid': [c for c in df_attempts.columns if c.startswith('Hybrid_')],
    'Pure_LLM': [c for c in df_attempts.columns if c.startswith('PureLLM_')]
}

# Calculate mean attempts per game for each category
anova_data = []
for game_num in range(100):
    row = {'Game': game_num + 1}
    for cat_name, cols in categories.items():
        valid_cols = [c for c in cols if c in df_attempts.columns]
        if valid_cols:
            values = df_attempts.loc[game_num, valid_cols].dropna()
            row[cat_name] = values.mean() if len(values) > 0 else np.nan
    anova_data.append(row)

df_anova = pd.DataFrame(anova_data)

# Reshape for ANOVA
anova_long = df_anova.melt(id_vars=['Game'], var_name='Category', value_name='Attempts')
anova_long = anova_long.dropna()

# Run one-way ANOVA
groups = [group['Attempts'].values for name, group in anova_long.groupby('Category')]
f_stat, p_value = stats.f_oneway(*groups)

print(f"One-Way ANOVA Results (Attempts):")
print(f"  F-statistic: {f_stat:.4f}")
print(f"  p-value: {p_value:.6f}")
print(f"  Significant: {'Yes' if p_value < 0.05 else 'No'} (α=0.05)")
print()

# Descriptive stats by category
print("Descriptive Statistics by Category:")
desc_stats = anova_long.groupby('Category')['Attempts'].agg(['mean', 'std', 'count'])
print(desc_stats.to_string())
print()

# ============================================================================
# STEP 9: Run Repeated Measures ANOVA on Hamming Distance
# ============================================================================
print("STEP 9: Running Repeated Measures ANOVA on Hamming Distance...")
print("-"*80)

# Load hamming per round data
hamming_round_file = DATA_DIR / "per_round_stats" / "hamming_per_round.zip"
if not hamming_round_file.exists():
    # Create from True CSS data for now
    print("Creating Hamming per round data...")

    # For repeated measures, we need: Subject (Game), Round, Approach, Hamming
    rm_data = []

    # True CSS
    for game_idx, row in true_css.iterrows():
        for round_num in range(1, 7):
            h_col = f'hamming_{round_num}'
            if h_col in row and pd.notna(row[h_col]):
                rm_data.append({
                    'Game': game_idx + 1,
                    'Round': round_num,
                    'Approach': 'CSS',
                    'Hamming': row[h_col]
                })

    # Load other algorithms for comparison
    algo_file = BASE_DIR / "results/algorithms/raw data/algorithm_results_20251211_175156.csv"
    df_algo = pd.read_csv(algo_file)

    for strategy in ['voi', 'random']:
        strategy_data = df_algo[df_algo['strategy'] == strategy]
        for game_idx, row in strategy_data.iterrows():
            game_num = row['game_number']
            for round_num in range(1, 7):
                h_col = f'hamming_{round_num}'
                if h_col in row and pd.notna(row[h_col]):
                    rm_data.append({
                        'Game': game_num,
                        'Round': round_num,
                        'Approach': strategy.upper(),
                        'Hamming': row[h_col]
                    })

    df_rm = pd.DataFrame(rm_data)
else:
    print("Loading existing hamming per round data...")
    df_rm = pd.read_csv(hamming_round_file)

# Run Repeated Measures ANOVA using pingouin
if len(df_rm) > 0:
    try:
        # Need balanced data - use only games that have data for all approaches and rounds
        pivot = df_rm.pivot_table(index=['Game', 'Round'], columns='Approach', values='Hamming')
        valid_games = pivot.dropna().reset_index()['Game'].unique()

        df_rm_balanced = df_rm[df_rm['Game'].isin(valid_games)]

        if len(df_rm_balanced) > 0:
            rm_anova = pg.rm_anova(data=df_rm_balanced, dv='Hamming', within=['Round', 'Approach'], subject='Game')
            print("\nRepeated Measures ANOVA Results (Hamming Distance):")
            print(rm_anova.to_string())
        else:
            print("Not enough balanced data for repeated measures ANOVA")
    except Exception as e:
        print(f"Error running RM-ANOVA: {e}")

        # Fall back to simpler analysis
        print("\nFalling back to simple Round effect ANOVA...")
        round_means = df_rm.groupby('Round')['Hamming'].mean()
        print("Mean Hamming by Round:")
        print(round_means)
print()

# ============================================================================
# STEP 10: Save Results Summary
# ============================================================================
print("STEP 10: Saving Results Summary...")
print("-"*80)

results_summary = {
    'timestamp': datetime.now().isoformat(),
    'true_css_stats': {
        'win_rate': float(true_css['won'].mean() * 100),
        'avg_attempts': float(true_css[true_css['won']==True]['attempts'].mean()),
        'games': int(len(true_css))
    },
    'anova_attempts': {
        'f_statistic': float(f_stat),
        'p_value': float(p_value),
        'significant': p_value < 0.05
    }
}

import json
with open(OUTPUT_DIR / 'anova_results_true_css.json', 'w') as f:
    json.dump(results_summary, f, indent=2)

print(f"Saved: {OUTPUT_DIR / 'anova_results_true_css.json'}")

print()
print("="*80)
print("ALL UPDATES COMPLETE!")
print("="*80)
