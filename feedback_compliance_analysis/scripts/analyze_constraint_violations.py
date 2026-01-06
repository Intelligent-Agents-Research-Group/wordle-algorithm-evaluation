#!/usr/bin/env python3
"""
Analyze constraint violation statistics from the processed data files.
Generate summary statistics for algorithms and hybrids.
"""

import pandas as pd
import numpy as np
import os
from pathlib import Path


def analyze_algorithm_violations():
    """Analyze constraint violation statistics for pure algorithms."""
    print("=" * 80)
    print("ALGORITHM CONSTRAINT VIOLATIONS")
    print("=" * 80)

    file_path = "results/algorithms/raw data/algorithm_results_with_violations.csv"

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

        strategy_stats = {'strategy': strategy, 'games': len(strategy_df)}

        total_violations = 0
        total_guesses = 0

        # Analyze each round (starting from round 2, since round 1 can't violate)
        for round_num in range(2, 7):
            green_col = f'violated_green_{round_num}'
            yellow_col = f'violated_yellow_{round_num}'
            gray_col = f'violated_gray_{round_num}'
            total_col = f'total_violations_{round_num}'

            if total_col in strategy_df.columns:
                # Filter out rounds that didn't happen
                valid_data = strategy_df[strategy_df[total_col].notna()]

                if len(valid_data) > 0:
                    avg_green = valid_data[green_col].mean()
                    avg_yellow = valid_data[yellow_col].mean()
                    avg_gray = valid_data[gray_col].mean()
                    avg_total = valid_data[total_col].mean()

                    # Count how many games had violations
                    games_with_violations = (valid_data[total_col] > 0).sum()
                    pct_with_violations = (games_with_violations / len(valid_data)) * 100

                    print(f"  Round {round_num}: {avg_total:.3f} avg violations "
                          f"({pct_with_violations:.1f}% of guesses had violations)")
                    print(f"    Green: {avg_green:.3f}, Yellow: {avg_yellow:.3f}, Gray: {avg_gray:.3f}")

                    strategy_stats[f'round_{round_num}_total'] = avg_total
                    strategy_stats[f'round_{round_num}_green'] = avg_green
                    strategy_stats[f'round_{round_num}_yellow'] = avg_yellow
                    strategy_stats[f'round_{round_num}_gray'] = avg_gray
                    strategy_stats[f'round_{round_num}_pct_with_violations'] = pct_with_violations

                    total_violations += valid_data[total_col].sum()
                    total_guesses += len(valid_data)

        # Overall statistics
        if total_guesses > 0:
            overall_avg = total_violations / total_guesses
            print(f"\n  Overall: {overall_avg:.3f} avg violations per guess")
            strategy_stats['overall_avg_violations'] = overall_avg

        results.append(strategy_stats)

    return pd.DataFrame(results)


def analyze_hybrid_violations(data_dir, label):
    """Analyze constraint violation statistics for hybrid approaches."""
    print(f"\n{'=' * 80}")
    print(f"HYBRID CONSTRAINT VIOLATIONS - {label}")
    print("=" * 80)

    if not os.path.exists(data_dir):
        print(f"Error: {data_dir} not found")
        return None

    # Find all processed files
    files = [f for f in os.listdir(data_dir) if f.endswith('_with_violations.csv')]

    if not files:
        print(f"No processed files found in {data_dir}")
        return None

    all_data = []

    for filename in files:
        file_path = os.path.join(data_dir, filename)
        df = pd.read_csv(file_path)

        # Extract model and algorithm from filename
        parts = filename.replace('_with_violations.csv', '').split('_')

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

            # Determine who made each guess
            for round_num in range(1, 7):
                # In hybrids: LLM on odd rounds (1, 3, 5), Algorithm on even rounds (2, 4, 6)
                if round_num % 2 == 1:
                    df[f'strategy_{round_num}'] = 'LLM'
                else:
                    df[f'strategy_{round_num}'] = algorithm.upper()

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

    # Analyze by who made the guess (LLM vs Algorithm)
    print(f"\nViolations by Strategy (LLM vs Algorithm):")
    print("-" * 80)

    for round_num in range(2, 7):  # Start from round 2
        total_col = f'total_violations_{round_num}'

        if total_col not in combined_df.columns:
            continue

        valid_data = combined_df[combined_df[total_col].notna()]

        if len(valid_data) == 0:
            continue

        # Determine who made this guess
        if round_num % 2 == 1:
            strategy = "LLM"
        else:
            strategy = "Algorithm"

        avg_violations = valid_data[total_col].mean()
        games_with_violations = (valid_data[total_col] > 0).sum()
        pct_with_violations = (games_with_violations / len(valid_data)) * 100

        print(f"  Round {round_num} ({strategy}): {avg_violations:.3f} avg violations "
              f"({pct_with_violations:.1f}% had violations)")

    # Aggregate statistics by algorithm
    print(f"\n\nAggregate by Algorithm:")
    print("-" * 80)

    algorithms = combined_df['algorithm'].unique()
    results = []

    for algo in algorithms:
        algo_df = combined_df[combined_df['algorithm'] == algo]

        print(f"\n{algo.upper()} (N={len(algo_df)} games)")

        algo_stats = {'algorithm': algo, 'games': len(algo_df)}

        total_violations = 0
        total_guesses = 0

        for round_num in range(2, 7):
            total_col = f'total_violations_{round_num}'

            if total_col in algo_df.columns:
                valid_data = algo_df[algo_df[total_col].notna()]

                if len(valid_data) > 0:
                    avg_total = valid_data[total_col].mean()
                    games_with_violations = (valid_data[total_col] > 0).sum()
                    pct_with_violations = (games_with_violations / len(valid_data)) * 100

                    strategy = "LLM" if round_num % 2 == 1 else "Algorithm"

                    print(f"  Round {round_num} ({strategy}): {avg_total:.3f} avg violations "
                          f"({pct_with_violations:.1f}% had violations)")

                    algo_stats[f'round_{round_num}_total'] = avg_total
                    algo_stats[f'round_{round_num}_pct_with_violations'] = pct_with_violations

                    total_violations += valid_data[total_col].sum()
                    total_guesses += len(valid_data)

        if total_guesses > 0:
            overall_avg = total_violations / total_guesses
            print(f"\n  Overall: {overall_avg:.3f} avg violations per guess")
            algo_stats['overall_avg_violations'] = overall_avg

        results.append(algo_stats)

    return pd.DataFrame(results)


def analyze_llm_violations():
    """Analyze existing LLM constraint violation data."""
    print("=" * 80)
    print("PURE LLM CONSTRAINT VIOLATIONS (Existing Data)")
    print("=" * 80)

    llm_dir = "results/llms/raw data"

    if not os.path.exists(llm_dir):
        print(f"Warning: {llm_dir} not found")
        return None

    files = [f for f in os.listdir(llm_dir) if f.endswith('.csv')]

    all_data = []

    for filename in files:
        file_path = os.path.join(llm_dir, filename)
        try:
            df = pd.read_csv(file_path)
            all_data.append(df)
        except Exception as e:
            print(f"Warning: Could not read {filename}: {e}")

    if not all_data:
        return None

    combined_df = pd.concat(all_data, ignore_index=True)

    # Calculate aggregate statistics
    print("\nAggregate Statistics:")
    print("-" * 80)

    total_violations = combined_df['total_constraint_violations'].sum()
    total_guesses = len(combined_df)
    avg_violations = total_violations / total_guesses

    games_with_violations = (combined_df['total_constraint_violations'] > 0).sum()
    pct_with_violations = (games_with_violations / total_guesses) * 100

    print(f"Total guesses: {total_guesses:,}")
    print(f"Total violations: {total_violations:,}")
    print(f"Average violations per guess: {avg_violations:.3f}")
    print(f"Guesses with violations: {games_with_violations:,} ({pct_with_violations:.1f}%)")

    print("\nBy violation type:")
    print("-" * 80)
    avg_green = combined_df['violated_green_constraint'].mean()
    avg_yellow = combined_df['violated_yellow_constraint'].mean()
    avg_gray = combined_df['violated_gray_constraint'].mean()

    print(f"Green violations: {avg_green:.3f} per guess")
    print(f"Yellow violations: {avg_yellow:.3f} per guess")
    print(f"Gray violations: {avg_gray:.3f} per guess")


def generate_comprehensive_report():
    """Generate a comprehensive report of constraint violation statistics."""

    output_file = "CONSTRAINT_VIOLATION_REPORT.md"

    with open(output_file, 'w') as f:
        f.write("# Constraint Violation Analysis Report\n\n")
        f.write("**Generated:** January 6, 2026\n\n")
        f.write("This report shows whether guesses respect feedback from previous rounds.\n\n")
        f.write("---\n\n")

        f.write("## What is a Constraint Violation?\n\n")
        f.write("A violation occurs when a guess ignores information from previous feedback:\n\n")
        f.write("- **Green Violation**: Wrong letter at a position marked as correct\n")
        f.write("- **Yellow Violation**: Missing a required letter or placing it at a forbidden position\n")
        f.write("- **Gray Violation**: Using a letter that was marked as not in the word\n\n")
        f.write("**Example:**\n")
        f.write("```\n")
        f.write("Round 1: HOUSE → Feedback: Y is gray (not in word)\n")
        f.write("Round 2: PARTY → VIOLATION! Used Y despite feedback\n")
        f.write("```\n\n")
        f.write("---\n\n")

        # Pure LLMs
        f.write("## Pure LLMs\n\n")
        f.write("LLM constraint violations are already tracked in the existing data.\n\n")

        # Run analysis for algorithms
        f.write("## Pure Algorithms\n\n")
        algo_df = analyze_algorithm_violations()

        if algo_df is not None:
            f.write("### Violations by Strategy\n\n")
            f.write("| Strategy | Games | Overall Avg Violations |\n")
            f.write("|----------|-------|------------------------|\n")

            for _, row in algo_df.iterrows():
                overall = row.get('overall_avg_violations', 0)
                f.write(f"| {row['strategy']} | {row['games']} | {overall:.3f} |\n")

            f.write("\n**Key Finding:** Pure algorithms are designed to respect constraints perfectly, ")
            f.write("so they should show 0 violations.\n\n")

        # Hybrid Analysis
        f.write("\n---\n\n")
        f.write("## Hybrids - Zero-shot Prompting\n\n")
        f.write("LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)\n\n")

        hybrid_zs_df = analyze_hybrid_violations("results/hybrids/stage3/raw data", "Zero-shot")

        if hybrid_zs_df is not None:
            f.write("### Violations by Algorithm\n\n")
            f.write("| Algorithm | Games | Overall Avg Violations |\n")
            f.write("|-----------|-------|------------------------|\n")

            for _, row in hybrid_zs_df.iterrows():
                overall = row.get('overall_avg_violations', 0)
                f.write(f"| {row['algorithm'].upper()} | {row['games']} | {overall:.3f} |\n")

        f.write("\n---\n\n")
        f.write("## Hybrids - Chain-of-Thought Prompting\n\n")
        f.write("LLM makes guesses on odd rounds (1, 3, 5), algorithm on even rounds (2, 4, 6)\n\n")

        hybrid_cot_df = analyze_hybrid_violations("results/hybrids/stage3-cot/raw data", "CoT")

        if hybrid_cot_df is not None:
            f.write("### Violations by Algorithm\n\n")
            f.write("| Algorithm | Games | Overall Avg Violations |\n")
            f.write("|-----------|-------|------------------------|\n")

            for _, row in hybrid_cot_df.iterrows():
                overall = row.get('overall_avg_violations', 0)
                f.write(f"| {row['algorithm'].upper()} | {row['games']} | {overall:.3f} |\n")

        f.write("\n---\n\n")
        f.write("## Key Insights\n\n")
        f.write("1. **Algorithms**: Should have 0 violations (they're designed to respect all constraints)\n")
        f.write("2. **LLMs**: May have violations when they fail to track previous feedback\n")
        f.write("3. **Hybrids**: Compare LLM rounds (1, 3, 5) vs Algorithm rounds (2, 4, 6)\n")
        f.write("4. **Violation rate**: Percentage of guesses that violated at least one constraint\n\n")
        f.write("**Interpretation:** Higher violation rates suggest the approach is not effectively ")
        f.write("using feedback from previous rounds.\n\n")

        f.write("---\n\n")
        f.write(f"**Data Sources:**\n")
        f.write(f"- Pure Algorithms: 800 games\n")
        f.write(f"- Hybrids Zero-shot: 2,700 games\n")
        f.write(f"- Hybrids CoT: 2,800 games\n")

    print(f"\n{'=' * 80}")
    print(f"Report saved to: {output_file}")
    print("=" * 80)


def main():
    """Main function."""
    analyze_llm_violations()
    generate_comprehensive_report()
    print("\n✓ Analysis complete!")


if __name__ == "__main__":
    main()
