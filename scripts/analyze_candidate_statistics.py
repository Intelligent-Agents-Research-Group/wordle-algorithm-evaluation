#!/usr/bin/env python3
"""
Analyze candidate statistics from the processed data files.
Generate summary statistics for algorithms and hybrids.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path


def analyze_algorithm_candidates():
    """Analyze candidate statistics for pure algorithms."""
    print("=" * 80)
    print("ALGORITHM CANDIDATE STATISTICS")
    print("=" * 80)

    file_path = "results/algorithms/raw data/algorithm_results_with_candidates.csv"

    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        return None

    df = pd.read_csv(file_path)

    # Get unique strategies
    strategies = df['strategy'].unique()

    results = []

    for strategy in strategies:
        strategy_df = df[df['strategy'] == strategy]

        print(f"\n{strategy}")
        print("-" * 80)

        strategy_stats = {'strategy': strategy}

        # Analyze each round
        for round_num in range(1, 7):
            before_col = f'candidates_before_{round_num}'
            after_col = f'candidates_after_{round_num}'
            reduction_col = f'reduction_rate_{round_num}'

            if before_col in strategy_df.columns:
                # Filter out NaN values (rounds that didn't happen)
                valid_data = strategy_df[strategy_df[before_col].notna()]

                if len(valid_data) > 0:
                    avg_before = valid_data[before_col].mean()
                    avg_after = valid_data[after_col].mean()
                    avg_reduction = valid_data[reduction_col].mean()

                    print(f"  Round {round_num}: {avg_before:.1f} → {avg_after:.1f} "
                          f"({avg_reduction:.2f}% reduction)")

                    strategy_stats[f'round_{round_num}_before'] = avg_before
                    strategy_stats[f'round_{round_num}_after'] = avg_after
                    strategy_stats[f'round_{round_num}_reduction'] = avg_reduction

        results.append(strategy_stats)

    return pd.DataFrame(results)


def analyze_hybrid_candidates(data_dir, label):
    """Analyze candidate statistics for hybrid approaches."""
    print(f"\n{'=' * 80}")
    print(f"HYBRID CANDIDATE STATISTICS - {label}")
    print("=" * 80)

    if not os.path.exists(data_dir):
        print(f"Error: {data_dir} not found")
        return None

    # Find all processed files
    files = [f for f in os.listdir(data_dir) if f.endswith('_with_candidates.csv')]

    if not files:
        print(f"No processed files found in {data_dir}")
        return None

    all_data = []

    for filename in files:
        file_path = os.path.join(data_dir, filename)
        df = pd.read_csv(file_path)

        # Extract model and algorithm from filename
        # Format: alternating_llm_first_<model>_<algorithm?>_<prompting?>_<timestamp>.csv
        parts = filename.replace('_with_candidates.csv', '').split('_')

        # Find model name (it's after 'first')
        try:
            first_idx = parts.index('first')
            model_parts = []
            for i in range(first_idx + 1, len(parts)):
                if parts[i] in ['random', 'voi', 'css', 'cot'] or parts[i].isdigit():
                    break
                model_parts.append(parts[i])
            model = '_'.join(model_parts)

            # Determine algorithm
            if 'random' in parts:
                algorithm = 'random'
            elif 'voi' in parts:
                algorithm = 'voi'
            else:
                algorithm = 'css'

            # Determine prompting
            prompting = 'CoT' if 'cot' in parts else 'Zero-shot'

        except Exception as e:
            print(f"Warning: Could not parse filename {filename}: {e}")
            continue

        df['model'] = model
        df['algorithm'] = algorithm
        df['prompting'] = prompting
        all_data.append(df)

    if not all_data:
        return None

    combined_df = pd.concat(all_data, ignore_index=True)

    # Aggregate statistics by algorithm
    print(f"\nAggregate by Algorithm:")
    print("-" * 80)

    algorithms = combined_df['algorithm'].unique()
    results = []

    for algo in algorithms:
        algo_df = combined_df[combined_df['algorithm'] == algo]

        print(f"\n{algo.upper()} (N={len(algo_df)} games)")

        algo_stats = {'algorithm': algo, 'games': len(algo_df)}

        for round_num in range(1, 7):
            before_col = f'candidates_before_{round_num}'
            after_col = f'candidates_after_{round_num}'
            reduction_col = f'reduction_rate_{round_num}'

            if before_col in algo_df.columns:
                valid_data = algo_df[algo_df[before_col].notna()]

                if len(valid_data) > 0:
                    avg_before = valid_data[before_col].mean()
                    avg_after = valid_data[after_col].mean()
                    avg_reduction = valid_data[reduction_col].mean()

                    print(f"  Round {round_num}: {avg_before:.1f} → {avg_after:.1f} "
                          f"({avg_reduction:.2f}% reduction)")

                    algo_stats[f'round_{round_num}_before'] = avg_before
                    algo_stats[f'round_{round_num}_after'] = avg_after
                    algo_stats[f'round_{round_num}_reduction'] = avg_reduction

        results.append(algo_stats)

    return pd.DataFrame(results)


def generate_comprehensive_report():
    """Generate a comprehensive report of candidate statistics."""

    output_file = "CANDIDATE_ANALYSIS_REPORT.md"

    with open(output_file, 'w') as f:
        f.write("# Candidate Count Analysis Report\n\n")
        f.write("**Generated:** January 6, 2026\n\n")
        f.write("This report shows how many valid word candidates remain after each guess.\n\n")
        f.write("---\n\n")

        # Algorithm Analysis
        f.write("## Pure Algorithms\n\n")
        f.write("Starting with 5,629 possible words, how do pure algorithms prune the search space?\n\n")

        algo_df = analyze_algorithm_candidates()

        if algo_df is not None:
            f.write("### Summary Table\n\n")
            f.write("| Strategy | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|----------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in algo_df.iterrows():
                f.write(f"| {row['strategy']} |")
                for round_num in range(1, 7):
                    after_col = f'round_{round_num}_after'
                    if after_col in row and not pd.isna(row[after_col]):
                        f.write(f" {row[after_col]:.0f} |")
                    else:
                        f.write(" - |")
                f.write("\n")

            f.write("\n### Reduction Rates\n\n")
            f.write("| Strategy | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|----------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in algo_df.iterrows():
                f.write(f"| {row['strategy']} |")
                for round_num in range(1, 7):
                    reduction_col = f'round_{round_num}_reduction'
                    if reduction_col in row and not pd.isna(row[reduction_col]):
                        f.write(f" {row[reduction_col]:.1f}% |")
                    else:
                        f.write(" - |")
                f.write("\n")

        # Hybrid Analysis - Zero-shot
        f.write("\n---\n\n")
        f.write("## Hybrids - Zero-shot Prompting\n\n")
        f.write("LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)\n\n")

        hybrid_zs_df = analyze_hybrid_candidates("results/hybrids/stage3/raw data", "Zero-shot")

        if hybrid_zs_df is not None:
            f.write("### Summary by Algorithm\n\n")
            f.write("| Algorithm | Games | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|-----------|-------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in hybrid_zs_df.iterrows():
                f.write(f"| {row['algorithm'].upper()} | {row['games']} |")
                for round_num in range(1, 7):
                    after_col = f'round_{round_num}_after'
                    if after_col in row and not pd.isna(row[after_col]):
                        f.write(f" {row[after_col]:.0f} |")
                    else:
                        f.write(" - |")
                f.write("\n")

            f.write("\n### Reduction Rates by Algorithm\n\n")
            f.write("| Algorithm | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|-----------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in hybrid_zs_df.iterrows():
                f.write(f"| {row['algorithm'].upper()} |")
                for round_num in range(1, 7):
                    reduction_col = f'round_{round_num}_reduction'
                    if reduction_col in row and not pd.isna(row[reduction_col]):
                        f.write(f" {row[reduction_col]:.1f}% |")
                    else:
                        f.write(" - |")
                f.write("\n")

        # Hybrid Analysis - CoT
        f.write("\n---\n\n")
        f.write("## Hybrids - Chain-of-Thought Prompting\n\n")
        f.write("LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)\n\n")

        hybrid_cot_df = analyze_hybrid_candidates("results/hybrids/stage3-cot/raw data", "CoT")

        if hybrid_cot_df is not None:
            f.write("### Summary by Algorithm\n\n")
            f.write("| Algorithm | Games | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|-----------|-------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in hybrid_cot_df.iterrows():
                f.write(f"| {row['algorithm'].upper()} | {row['games']} |")
                for round_num in range(1, 7):
                    after_col = f'round_{round_num}_after'
                    if after_col in row and not pd.isna(row[after_col]):
                        f.write(f" {row[after_col]:.0f} |")
                    else:
                        f.write(" - |")
                f.write("\n")

            f.write("\n### Reduction Rates by Algorithm\n\n")
            f.write("| Algorithm | Round 1 | Round 2 | Round 3 | Round 4 | Round 5 | Round 6 |\n")
            f.write("|-----------|---------|---------|---------|---------|---------|----------|\n")

            for _, row in hybrid_cot_df.iterrows():
                f.write(f"| {row['algorithm'].upper()} |")
                for round_num in range(1, 7):
                    reduction_col = f'round_{round_num}_reduction'
                    if reduction_col in row and not pd.isna(row[reduction_col]):
                        f.write(f" {row[reduction_col]:.1f}% |")
                    else:
                        f.write(" - |")
                f.write("\n")

        f.write("\n---\n\n")
        f.write("## Key Insights\n\n")
        f.write("1. **Starting point:** All approaches begin with 5,629 possible candidates\n")
        f.write("2. **First guess:** Observe how effectively each approach prunes the initial search space\n")
        f.write("3. **Convergence:** Track how quickly candidates decrease toward 1 (the answer)\n")
        f.write("4. **Strategy differences:** Compare how CSS, VOI, and Random differ in pruning patterns\n")
        f.write("5. **Hybrid effects:** See how LLM+algorithm alternation affects search space reduction\n")
        f.write("\n---\n\n")
        f.write(f"**Data Sources:**\n")
        f.write(f"- Pure Algorithms: 800 games (7 strategies × 100 games)\n")
        f.write(f"- Hybrids Zero-shot: 2,700 games (9 models × 3 algorithms × 100 games)\n")
        f.write(f"- Hybrids CoT: 2,800 games (9 models × 3 algorithms × 100 games + extras)\n")

    print(f"\n{'=' * 80}")
    print(f"Report saved to: {output_file}")
    print("=" * 80)


def main():
    """Main function."""
    generate_comprehensive_report()
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
