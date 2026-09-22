"""
Create wide-format CSV files for various metrics by game and approach.
Similar to ATTEMPTS_BY_GAME_AND_APPROACH.csv but for:
1. Hamming distance (final)
2. Levenshtein distance (final)
3. Convergence rate
4. Total feedback violations

Author: Kevin Scroggins
Date: January 9, 2026
"""

import pandas as pd
import numpy as np
from pathlib import Path
import re

def get_final_distance(row, distance_type='hamming', max_rounds=6):
    """Get the final distance before winning or at game end."""
    for round_num in range(max_rounds, 0, -1):
        col_name = f'{distance_type}_{round_num}'
        if col_name in row.index and pd.notna(row[col_name]):
            return row[col_name]
    return np.nan

def calculate_convergence_rate(row, distance_type='hamming', max_rounds=6):
    """Calculate convergence rate as total distance decrease per round."""
    distances = []
    for round_num in range(1, max_rounds + 1):
        col_name = f'{distance_type}_{round_num}'
        if col_name in row.index and pd.notna(row[col_name]):
            distances.append(row[col_name])
        else:
            break

    if len(distances) < 2:
        return np.nan

    # Convergence rate = (initial_distance - final_distance) / number_of_rounds
    initial = distances[0]
    final = distances[-1]
    num_rounds = len(distances)

    return (initial - final) / num_rounds

def calculate_total_violations(row, max_rounds=6):
    """Calculate total violations across all rounds."""
    total = 0
    for round_num in range(1, max_rounds + 1):
        col_name = f'total_violations_{round_num}'
        if col_name in row.index and pd.notna(row[col_name]):
            total += row[col_name]
    return total

def load_algorithm_data(metric_func, metric_name):
    """Load algorithm data and calculate metric."""
    # Try different file patterns
    possible_files = [
        'results/algorithms/raw data/algorithm_results_20251211_175156.csv',
        'results/algorithms/raw data/algorithm_results_with_violations.csv',
        'results/algorithms/raw data/algorithm_results_with_candidates.csv'
    ]

    df = None
    for file_path in possible_files:
        if Path(file_path).exists():
            df = pd.read_csv(file_path)
            break

    if df is None:
        print(f"Warning: No algorithm results file found")
        return pd.DataFrame()

    # Calculate metric for each game
    df[metric_name] = df.apply(metric_func, axis=1)

    # Create approach names
    df['approach'] = 'Pure_Algo_' + df['strategy']

    # Select only needed columns
    result = df[['game_number', 'approach', metric_name]].copy()

    return result

def load_hybrid_data(metric_func, metric_name, prompting='zero_shot'):
    """Load hybrid data and calculate metric."""
    if prompting == 'zero_shot':
        data_dir = Path('results/hybrids/stage3/raw data')
    else:
        data_dir = Path('results/hybrids/stage3-cot/raw data')

    if not data_dir.exists():
        print(f"Warning: Directory {data_dir} not found")
        return pd.DataFrame()

    # Find all hybrid CSV files
    csv_files = list(data_dir.glob('alternating_llm_first_*.csv'))

    # Group files by model and algorithm, keep only the latest timestamp
    file_groups = {}

    for file_path in csv_files:
        filename = file_path.stem

        # Extract model name and algorithm
        pattern = r'alternating_llm_first_(.+?)_(css|voi|random)(_cot)?_(\d+)'
        match = re.search(pattern, filename)

        if not match:
            continue

        model = match.group(1)
        algorithm = match.group(2)
        is_cot = match.group(3) is not None
        timestamp = match.group(4)

        # Skip if prompting doesn't match
        if (prompting == 'cot' and not is_cot) or (prompting == 'zero_shot' and is_cot):
            continue

        key = (model, algorithm, is_cot)

        # Keep file with latest timestamp
        if key not in file_groups or timestamp > file_groups[key][1]:
            file_groups[key] = (file_path, timestamp)

    all_data = []

    for (model, algorithm, is_cot), (file_path, _) in file_groups.items():
        # Read data
        df = pd.read_csv(file_path)

        # Calculate metric
        df[metric_name] = df.apply(metric_func, axis=1)

        # Create approach name
        prompting_suffix = 'CoT' if is_cot else 'ZeroShot'
        df['approach'] = f'Hybrid_{model}_{algorithm.upper()}_{prompting_suffix}'

        # Select only needed columns
        result = df[['game_number', 'approach', metric_name]].copy()
        all_data.append(result)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

def load_pure_llm_data(metric_func, metric_name):
    """Load pure LLM data and calculate metric."""
    data_dir = Path('results/llms/raw data')

    if not data_dir.exists():
        print(f"Warning: Directory {data_dir} not found")
        return pd.DataFrame()

    # Find all LLM CSV files
    csv_files = list(data_dir.glob('model_*.csv'))

    # Group files by model and prompting, keep only the latest timestamp
    file_groups = {}

    for file_path in csv_files:
        filename = file_path.stem

        # Parse filename
        # Format: model_<model_name>_chain-of-thought_<timestamp> or model_<model_name>_zero-shot_<timestamp>
        # Example: model_mistral_small_3.1_chain-of-thought_20251211_213959

        # Remove 'model_' prefix
        if filename.startswith('model_'):
            filename = filename[6:]

        parts = filename.split('_')

        # Check prompting type
        is_cot = 'chain-of-thought' in filename or 'cot' in filename.lower()

        # Find timestamp (starts with 8 digits)
        model_parts = []
        timestamp = None
        for i, part in enumerate(parts):
            if re.match(r'\d{8}', part):  # Found timestamp
                timestamp = '_'.join(parts[i:i+2]) if i+1 < len(parts) else part
                break
            # Skip prompting type indicators
            if part.lower() not in ['chain-of-thought', 'cot', 'zero-shot', 'zero', 'shot']:
                model_parts.append(part)

        model = '-'.join(model_parts)

        if not model or not timestamp:
            continue

        key = (model, is_cot)

        # Keep file with latest timestamp
        if key not in file_groups or timestamp > file_groups[key][1]:
            file_groups[key] = (file_path, timestamp)

    all_data = []

    for (model, is_cot), (file_path, _) in file_groups.items():
        # Read data
        try:
            df = pd.read_csv(file_path)
        except:
            continue

        # Calculate metric
        df[metric_name] = df.apply(metric_func, axis=1)

        # Create approach name
        prompting_suffix = 'CoT' if is_cot else 'ZeroShot'
        df['approach'] = f'PureLLM_{model}_{prompting_suffix}'

        # Select only needed columns
        result = df[['game_number', 'approach', metric_name]].copy()
        all_data.append(result)

    if not all_data:
        return pd.DataFrame()

    return pd.concat(all_data, ignore_index=True)

def create_wide_format_csv(metric_func, metric_name, output_file):
    """Create wide format CSV for a given metric."""
    print(f"\nCreating {output_file}...")

    # Load all data
    print("  Loading algorithm data...")
    algo_data = load_algorithm_data(metric_func, metric_name)

    print("  Loading hybrid zero-shot data...")
    hybrid_zs_data = load_hybrid_data(metric_func, metric_name, prompting='zero_shot')

    print("  Loading hybrid CoT data...")
    hybrid_cot_data = load_hybrid_data(metric_func, metric_name, prompting='cot')

    print("  Loading pure LLM data...")
    llm_data = load_pure_llm_data(metric_func, metric_name)

    # Combine all data
    all_data = pd.concat([
        algo_data,
        hybrid_zs_data,
        hybrid_cot_data,
        llm_data
    ], ignore_index=True)

    if all_data.empty:
        print(f"  Warning: No data found for {metric_name}")
        return

    print(f"  Total rows: {len(all_data)}")
    print(f"  Unique approaches: {all_data['approach'].nunique()}")

    # Pivot to wide format
    wide_df = all_data.pivot(index='game_number', columns='approach', values=metric_name)

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

def main():
    """Main function to create all metric CSVs."""
    print("=" * 70)
    print("Creating Metric CSVs by Game and Approach")
    print("=" * 70)

    # 1. Hamming Distance (Final)
    create_wide_format_csv(
        lambda row: get_final_distance(row, 'hamming'),
        'final_hamming_distance',
        'HAMMING_DISTANCE_BY_GAME_AND_APPROACH.csv'
    )

    # 2. Levenshtein Distance (Final)
    create_wide_format_csv(
        lambda row: get_final_distance(row, 'levenshtein'),
        'final_levenshtein_distance',
        'LEVENSHTEIN_DISTANCE_BY_GAME_AND_APPROACH.csv'
    )

    # 3. Convergence Rate (Hamming-based)
    create_wide_format_csv(
        lambda row: calculate_convergence_rate(row, 'hamming'),
        'convergence_rate',
        'CONVERGENCE_RATE_BY_GAME_AND_APPROACH.csv'
    )

    # 4. Total Violations
    create_wide_format_csv(
        calculate_total_violations,
        'total_violations',
        'TOTAL_VIOLATIONS_BY_GAME_AND_APPROACH.csv'
    )

    print("\n" + "=" * 70)
    print("All metric CSVs created successfully!")
    print("=" * 70)

if __name__ == '__main__':
    main()
