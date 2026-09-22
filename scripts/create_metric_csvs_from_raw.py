"""
Create wide-format CSV files for various metrics by game and approach.
Calculates metrics directly from raw data to ensure completeness.

Metrics:
1. Final Hamming distance
2. Final Levenshtein distance
3. Convergence rate
4. Total feedback violations

Author: Kevin Scroggins
Date: January 9, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re


def hamming_distance(s1, s2):
    """Calculate Hamming distance between two strings."""
    if len(s1) != len(s2):
        return None
    return sum(c1 != c2 for c1, c2 in zip(s1, s2))


def levenshtein_distance(s1, s2):
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # j+1 instead of j since previous_row and current_row are one character longer
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row

    return previous_row[-1]


def process_algorithm_data():
    """Process algorithm CSV files."""
    print("\nProcessing algorithm data...")

    file_path = Path('results/algorithms/raw data/algorithm_results_20251211_175156.csv')
    if not file_path.exists():
        print(f"  Warning: {file_path} not found")
        return pd.DataFrame()

    df = pd.read_csv(file_path)

    results = []

    for _, row in df.iterrows():
        game_num = row['game_number']
        target = row['target_word'].upper()
        strategy = row['strategy']
        approach = f'Pure_Algo_{strategy}'

        # Calculate metrics per round
        result = {
            'game_number': game_num,
            'approach': approach,
        }

        # Store distances and violations for each round
        for round_num in range(1, 7):
            guess_col = f'guess_{round_num}'

            if guess_col not in row.index or pd.isna(row[guess_col]):
                # No guess for this round
                result[f'hamming_{round_num}'] = np.nan
                result[f'levenshtein_{round_num}'] = np.nan
                result[f'violations_{round_num}'] = np.nan
            else:
                guess = str(row[guess_col]).upper()

                # Calculate distances
                result[f'hamming_{round_num}'] = hamming_distance(guess, target)
                result[f'levenshtein_{round_num}'] = levenshtein_distance(guess, target)

                # Get violations if available
                viol_col = f'total_violations_{round_num}'
                if viol_col in row.index and pd.notna(row[viol_col]):
                    result[f'violations_{round_num}'] = row[viol_col]
                else:
                    result[f'violations_{round_num}'] = 0

        results.append(result)

    df_results = pd.DataFrame(results)
    print(f"  Processed {len(df_results)} games")
    return df_results


def simplify_model_name(full_model_name):
    """Simplify model names to match ATTEMPTS file format."""
    # Map full names to simplified names
    name_map = {
        'codestral-22b': 'codestral-22b',
        'gemma-3-27b-it': 'gemma-27b',
        'granite-3.3-8b-instruct': 'granite-8b',
        'llama-3.1-70b-instruct': 'llama-3.1-70b',
        'llama-3.1-8b-instruct': 'llama-3.1-8b',
        'llama-3.1-nemotron-nano-8B-v1': 'nemotron-8b',
        'llama-3.3-70b-instruct': 'llama-3.3-70b',
        'mistral-7b-instruct': 'mistral-7b',
        'mistral-small-3.1': 'mistral-small',
    }
    return name_map.get(full_model_name, full_model_name)


def process_hybrid_data(prompting='zero_shot'):
    """Process hybrid CSV files."""
    print(f"\nProcessing hybrid {prompting} data...")

    if prompting == 'zero_shot':
        data_dir = Path('results/hybrids/stage3/raw data')
    else:
        data_dir = Path('results/hybrids/stage3-cot/raw data')

    if not data_dir.exists():
        print(f"  Warning: Directory {data_dir} not found")
        return pd.DataFrame()

    # Find all hybrid CSV files (excluding _with_candidates and _with_violations)
    csv_files = [f for f in data_dir.glob('alternating_llm_first_*.csv')
                 if '_with_' not in f.stem]

    # Group files by model and algorithm, keep only the latest timestamp
    file_groups = {}

    for file_path in csv_files:
        filename = file_path.stem

        # Extract model name and algorithm
        # Pattern 1: with algorithm specified (random/voi)
        # Format: alternating_llm_first_MODEL_(voi|random)(_cot)?_TIMESTAMP
        pattern1 = r'alternating_llm_first_(.+?)_(voi|random)(_cot)?_(\d+_\d+)'
        match1 = re.search(pattern1, filename)

        # Pattern 2: without algorithm (CSS is default)
        # Format: alternating_llm_first_MODEL(_cot)?_TIMESTAMP
        pattern2 = r'alternating_llm_first_(.+?)(_cot)?_(\d+_\d+)$'
        match2 = re.search(pattern2, filename) if not match1 else None

        if match1:
            model = match1.group(1)
            algorithm = match1.group(2)
            is_cot = match1.group(3) is not None
            timestamp = match1.group(4)
        elif match2:
            model = match2.group(1)
            algorithm = 'css'  # Default to CSS when not specified
            is_cot = match2.group(2) is not None
            timestamp = match2.group(3)
        else:
            continue

        # Skip if prompting doesn't match
        if (prompting == 'cot' and not is_cot) or (prompting == 'zero_shot' and is_cot):
            continue

        # Simplify model name
        model = simplify_model_name(model)

        key = (model, algorithm, is_cot)

        # Keep file with latest timestamp
        if key not in file_groups or timestamp > file_groups[key][1]:
            file_groups[key] = (file_path, timestamp)

    all_results = []

    for (model, algorithm, is_cot), (file_path, _) in file_groups.items():
        df = pd.read_csv(file_path)

        prompting_suffix = 'CoT' if is_cot else 'ZeroShot'
        # Match ATTEMPTS file naming: CSS, VOI, Random (capitalize Random)
        if algorithm == 'random':
            algo_str = 'Random'
        else:
            algo_str = algorithm.upper()
        approach = f'Hybrid_{model}_{algo_str}_{prompting_suffix}'

        for _, row in df.iterrows():
            game_num = row['game_number']
            target = row['target_word'].upper()

            # Calculate metrics per round
            result = {
                'game_number': game_num,
                'approach': approach,
            }

            # Store distances and violations for each round
            for round_num in range(1, 7):
                guess_col = f'guess_{round_num}'

                if guess_col not in row.index or pd.isna(row[guess_col]):
                    # No guess for this round
                    result[f'hamming_{round_num}'] = np.nan
                    result[f'levenshtein_{round_num}'] = np.nan
                    result[f'violations_{round_num}'] = np.nan
                else:
                    guess = str(row[guess_col]).upper()

                    # Calculate distances
                    result[f'hamming_{round_num}'] = hamming_distance(guess, target)
                    result[f'levenshtein_{round_num}'] = levenshtein_distance(guess, target)

                    # Get violations if available
                    viol_col = f'total_violations_{round_num}'
                    if viol_col in row.index and pd.notna(row[viol_col]):
                        result[f'violations_{round_num}'] = row[viol_col]
                    else:
                        result[f'violations_{round_num}'] = 0

            all_results.append(result)

    df_results = pd.DataFrame(all_results)
    print(f"  Processed {len(df_results)} games")
    return df_results


def process_pure_llm_data():
    """Process pure LLM CSV files."""
    print("\nProcessing pure LLM data...")

    data_dir = Path('results/llms/raw data')

    if not data_dir.exists():
        print(f"  Warning: Directory {data_dir} not found")
        return pd.DataFrame()

    # Find all LLM CSV files
    csv_files = list(data_dir.glob('model_*.csv'))

    # Group files by model and prompting, keep only the latest timestamp
    file_groups = {}

    for file_path in csv_files:
        filename = file_path.stem

        # Remove 'model_' prefix
        if filename.startswith('model_'):
            filename_clean = filename[6:]
        else:
            filename_clean = filename

        # Check prompting type
        is_cot = 'chain-of-thought' in filename or 'cot' in filename.lower()

        # Extract model name and timestamp
        parts = filename_clean.split('_')
        model_parts = []
        timestamp = None

        for i, part in enumerate(parts):
            if re.match(r'\d{8}', part):  # Found timestamp
                timestamp = '_'.join(parts[i:i+2]) if i+1 < len(parts) else part
                break
            # Skip prompting type indicators
            if part.lower() not in ['chain-of-thought', 'cot', 'zero-shot', 'zero', 'shot', 'chain', 'of', 'thought']:
                model_parts.append(part)

        model = '-'.join(model_parts)

        if not model or not timestamp:
            continue

        # Simplify model name to match ATTEMPTS format
        model = simplify_model_name(model)

        key = (model, is_cot)

        # Keep file with latest timestamp
        if key not in file_groups or timestamp > file_groups[key][1]:
            file_groups[key] = (file_path, timestamp)

    all_results = []

    for (model, is_cot), (file_path, _) in file_groups.items():
        try:
            df = pd.read_csv(file_path)
        except Exception as e:
            print(f"  Error reading {file_path}: {e}")
            continue

        prompting_suffix = 'CoT' if is_cot else 'ZeroShot'
        approach = f'PureLLM_{model}_{prompting_suffix}'

        # Group by game_id
        for game_id, game_df in df.groupby('game_id'):
            game_df = game_df.sort_values('attempt_number')

            if len(game_df) == 0:
                continue

            target = game_df.iloc[0]['target_word'].upper()
            game_num = game_id + 1  # game_id is 0-indexed

            # Calculate metrics per round
            result = {
                'game_number': game_num,
                'approach': approach,
            }

            # Store distances and violations for each round
            for round_num in range(1, 7):
                # Find the attempt for this round
                attempt_rows = game_df[game_df['attempt_number'] == round_num]

                if len(attempt_rows) == 0 or pd.isna(attempt_rows.iloc[0]['guess']):
                    # No guess for this round
                    result[f'hamming_{round_num}'] = np.nan
                    result[f'levenshtein_{round_num}'] = np.nan
                    result[f'violations_{round_num}'] = np.nan
                else:
                    attempt = attempt_rows.iloc[0]
                    guess = str(attempt['guess']).upper()

                    # Calculate distances
                    result[f'hamming_{round_num}'] = hamming_distance(guess, target)
                    result[f'levenshtein_{round_num}'] = levenshtein_distance(guess, target)

                    # Get violations if available
                    if 'total_constraint_violations' in attempt.index and pd.notna(attempt['total_constraint_violations']):
                        result[f'violations_{round_num}'] = attempt['total_constraint_violations']
                    else:
                        result[f'violations_{round_num}'] = 0

            all_results.append(result)

    df_results = pd.DataFrame(all_results)
    print(f"  Processed {len(df_results)} games")
    return df_results


def create_wide_format_csv(df_long, metric_col, output_file):
    """Create wide format CSV from long format data."""
    print(f"\nCreating {output_file}...")

    # Pivot to wide format
    wide_df = df_long.pivot(index='game_number', columns='approach', values=metric_col)

    # Sort columns to match ATTEMPTS_BY_GAME_AND_APPROACH.csv order
    # Order: Hybrids, PureLLMs, Pure_Algos
    hybrid_cols = sorted([c for c in wide_df.columns if c.startswith('Hybrid_')])
    llm_cols = sorted([c for c in wide_df.columns if c.startswith('PureLLM_')])
    algo_cols = sorted([c for c in wide_df.columns if c.startswith('Pure_Algo_')])

    ordered_cols = hybrid_cols + llm_cols + algo_cols
    wide_df = wide_df[ordered_cols]

    # Reset index to make game_number a column
    wide_df = wide_df.reset_index()
    wide_df = wide_df.rename(columns={'game_number': 'Game_Number'})

    # Sort by game number
    wide_df = wide_df.sort_values('Game_Number')

    # Save to CSV
    output_path = Path('results') / output_file
    wide_df.to_csv(output_path, index=False)
    print(f"  Saved to {output_path}")
    print(f"  Shape: {wide_df.shape}")
    print(f"  Approaches: {len(ordered_cols)} ({len(hybrid_cols)} Hybrid, {len(llm_cols)} PureLLM, {len(algo_cols)} Pure_Algo)")


def main():
    """Main function to create all metric CSVs."""
    print("=" * 70)
    print("Creating Per-Round Metric CSVs from Raw Data")
    print("=" * 70)

    # Process all data sources
    algo_data = process_algorithm_data()
    hybrid_zs_data = process_hybrid_data('zero_shot')
    hybrid_cot_data = process_hybrid_data('cot')
    llm_data = process_pure_llm_data()

    # Combine all data
    print("\nCombining all data...")
    all_data = pd.concat([
        algo_data,
        hybrid_zs_data,
        hybrid_cot_data,
        llm_data
    ], ignore_index=True)

    print(f"Total rows: {len(all_data)}")
    print(f"Unique approaches: {all_data['approach'].nunique()}")
    print(f"Unique games: {all_data['game_number'].nunique()}")

    # Create wide format CSVs for each metric and each round
    print("\n" + "=" * 70)
    print("Creating Hamming Distance files (6 rounds)...")
    print("=" * 70)
    for round_num in range(1, 7):
        create_wide_format_csv(all_data, f'hamming_{round_num}', f'HAMMING_DISTANCE_ROUND_{round_num}_BY_GAME_AND_APPROACH.csv')

    print("\n" + "=" * 70)
    print("Creating Levenshtein Distance files (6 rounds)...")
    print("=" * 70)
    for round_num in range(1, 7):
        create_wide_format_csv(all_data, f'levenshtein_{round_num}', f'LEVENSHTEIN_DISTANCE_ROUND_{round_num}_BY_GAME_AND_APPROACH.csv')

    print("\n" + "=" * 70)
    print("Creating Violations files (6 rounds)...")
    print("=" * 70)
    for round_num in range(1, 7):
        create_wide_format_csv(all_data, f'violations_{round_num}', f'VIOLATIONS_ROUND_{round_num}_BY_GAME_AND_APPROACH.csv')

    print("\n" + "=" * 70)
    print("All per-round metric CSVs created successfully!")
    print("=" * 70)
    print("\nTotal files created: 18")
    print("  - 6 Hamming distance files (one per round)")
    print("  - 6 Levenshtein distance files (one per round)")
    print("  - 6 Violations files (one per round)")


if __name__ == '__main__':
    main()
